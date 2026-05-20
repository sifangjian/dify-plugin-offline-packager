"""
打包服务模块

该模块实现了 Dify 插件离线打包的核心业务逻辑，包括：
- 任务队列管理：基于 asyncio.Queue 实现异步任务调度
- 打包流程编排：协调下载、依赖解析、依赖下载、打包等步骤
- 事件推送：通过 SSE 实时推送打包进度
- 会话管理：支持批量打包多个插件

打包流程：
1. 用户提交打包请求，创建 Session 和 Task
2. Task 入队等待后台消费者处理
3. 消费者依次执行：下载 → 解析依赖 → 下载依赖 → 打包
4. 每个步骤通过 SSE 推送进度事件
5. 打包完成后用户可下载离线包
"""

import asyncio
import contextlib
import os
import sys
import time
import uuid
import zipfile
from collections.abc import Callable
from datetime import datetime

import httpx

from app.core.config import Settings
from app.models.plugin import (
    Architecture,
    PackPluginItem,
    PackSessionInfo,
    PackStep,
    PackTaskInfo,
    PluginSource,
    SessionStatus,
    TaskStatus,
)
from app.models.sse import (
    STEP_MESSAGES,
    SessionCompletedEvent,
    StepProgressEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    TaskSuccessEvent,
)
from app.services.marketplace import MarketplaceService
from app.services.storage import StorageService

ARCHITECTURE_PLATFORM_MAP: dict[Architecture, str] = {
    Architecture.LINUX_AMD64: "manylinux2014_x86_64",
    Architecture.LINUX_ARM64: "manylinux2014_aarch64",
    Architecture.DARWIN_AMD64: "macosx_10_9_x86_64",
    Architecture.DARWIN_ARM64: "macosx_11_0_arm64",
}


class PackageStepError(Exception):
    """
    打包步骤异常

    当某个打包步骤失败时抛出，包含失败步骤、错误消息和原始错误信息。

    Attributes:
        step: 失败的打包步骤
        message: 用户友好的错误消息
        raw_error: 原始错误详情，用于调试
    """

    def __init__(self, step: PackStep, message: str, raw_error: str):
        self.step = step
        self.message = message
        self.raw_error = raw_error
        super().__init__(message)


class PackagerService:
    """
    打包服务核心类

    负责管理整个打包生命周期，包括任务调度、依赖解析、离线包生成等。
    采用生产者-消费者模式，支持并发处理多个打包请求。

    Attributes:
        _httpx_client: HTTP 客户端，用于调用 Marketplace API
        _settings: 应用配置
        _storage: 存储服务，管理文件系统操作
        _marketplace: Marketplace 服务，用于下载插件
        _queue: 异步任务队列
        _sessions: 打包会话字典，session_id -> PackSessionInfo
        _tasks: 打包任务字典，task_id -> PackTaskInfo
        _subscribers: SSE 订阅者字典，session_id -> list[Queue]
        _consumer_task: 后台消费者协程任务
    """

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        settings: Settings,
        storage: StorageService,
    ):
        """
        初始化打包服务

        Args:
            httpx_client: 异步 HTTP 客户端
            settings: 应用配置对象
            storage: 存储服务实例
        """
        self._httpx_client = httpx_client
        self._settings = settings
        self._storage = storage
        self._marketplace = MarketplaceService(client=httpx_client, base_url=settings.MARKETPLACE_API_URL)
        self._queue: asyncio.Queue[PackTaskInfo] = asyncio.Queue()
        self._sessions: dict[str, PackSessionInfo] = {}
        self._tasks: dict[str, PackTaskInfo] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._consumer_task: asyncio.Task | None = None
        self._running_processes: dict[str, asyncio.subprocess.Process] = {}

    def start(self) -> None:
        """
        启动打包服务

        创建后台消费者协程，开始处理队列中的任务。
        应在应用启动时调用。
        """
        self._consumer_task = asyncio.create_task(self._queue_consumer())

    async def stop(self) -> None:
        """
        停止打包服务

        取消后台消费者协程并等待其结束。
        应在应用关闭时调用。
        """
        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task

    async def submit_session(self, plugins: list[PackPluginItem]) -> PackSessionInfo:
        """
        提交打包会话

        创建一个新的打包会话，为每个插件创建对应的任务并加入队列。
        支持批量打包多个插件。

        Args:
            plugins: 待打包的插件列表，包含作者、名称、版本和来源信息

        Returns:
            PackSessionInfo: 创建的会话信息，包含 session_id 和任务列表
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        tasks = []
        for plugin in plugins:
            task_id = str(uuid.uuid4())
            task = PackTaskInfo(
                task_id=task_id,
                session_id=session_id,
                author=plugin.author,
                name=plugin.name,
                version=plugin.version,
                source=plugin.source,
                architecture=plugin.architecture,
                status=TaskStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            self._tasks[task_id] = task
            tasks.append(task)
            await self._queue.put(task)

        session = PackSessionInfo(
            session_id=session_id,
            task_ids=[t.task_id for t in tasks],
            created_at=now,
        )
        self._sessions[session_id] = session
        return session

    async def _queue_consumer(self) -> None:
        """
        任务队列消费者

        后台协程，持续从队列中取出任务并处理。
        每个任务处理完成后检查会话是否全部完成。
        """
        while True:
            task = await self._queue.get()
            try:
                await self._process_task(task)
            except Exception:
                pass
            finally:
                self._queue.task_done()
                self._check_session_completion(task.session_id)

    def _is_task_cancelled(self, task: PackTaskInfo) -> bool:
        """
        检查任务是否已被取消

        Args:
            task: 任务信息

        Returns:
            bool: 任务已取消返回 True
        """
        return task.status == TaskStatus.CANCELLED

    async def _run_subprocess(
        self,
        task: PackTaskInfo,
        cmd: list[str],
        cwd: str | None = None,
    ) -> tuple[int, bytes, bytes]:
        """
        运行子进程，支持取消时终止

        Args:
            task: 任务信息，用于跟踪进程
            cmd: 命令和参数列表
            cwd: 工作目录

        Returns:
            tuple[int, bytes, bytes]: 返回码、标准输出、标准错误

        Raises:
            RuntimeError: 任务被取消时抛出
        """
        print(f"[subprocess] Running: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._running_processes[task.task_id] = proc

        try:
            stdout, stderr = await proc.communicate()
            print(f"[subprocess] Exit code: {proc.returncode}")
            if stdout:
                print(f"[subprocess] stdout: {stdout.decode()[:500]}")
            if self._is_task_cancelled(task):
                raise RuntimeError("Task cancelled")
            return proc.returncode or 0, stdout, stderr
        finally:
            self._running_processes.pop(task.task_id, None)

    def _terminate_process(self, task_id: str) -> None:
        """
        终止指定任务的子进程

        Args:
            task_id: 任务ID
        """
        proc = self._running_processes.get(task_id)
        if proc and proc.returncode is None:
            proc.terminate()

    async def _run_subprocess_with_progress(
        self,
        task: PackTaskInfo,
        cmd: list[str],
        cwd: str | None = None,
        progress_callback: Callable | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        print(f"[subprocess] Running: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._running_processes[task.task_id] = proc

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def read_stream(stream, lines: list[str], is_stderr: bool):
            buf = b""
            while True:
                chunk = await stream.read(1024)
                if not chunk:
                    if buf:
                        line_str = buf.decode(errors="replace").strip()
                        if line_str:
                            lines.append(line_str)
                            print(f"[{'stderr' if is_stderr else 'stdout'}] {line_str}")
                            if progress_callback:
                                progress_callback(line_str)
                    break
                buf += chunk
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    line_str = line_bytes.decode(errors="replace").strip()
                    if line_str:
                        lines.append(line_str)
                        print(f"[{'stderr' if is_stderr else 'stdout'}] {line_str}")
                        if progress_callback:
                            progress_callback(line_str)
                if b"\r" in buf:
                    parts = buf.split(b"\r")
                    last_part = parts[-1]
                    line_str = last_part.decode(errors="replace").strip()
                    if line_str and line_str != (lines[-1] if lines else ""):
                        if lines and not lines[-1].endswith(line_str):
                            lines[-1] = line_str
                        else:
                            lines.append(line_str)
                        print(f"[{'stderr' if is_stderr else 'stdout'}] {line_str}")
                        if progress_callback:
                            progress_callback(line_str)
                    buf = last_part

        try:
            await asyncio.gather(
                read_stream(proc.stdout, stdout_lines, False),
                read_stream(proc.stderr, stderr_lines, True),
            )
            await proc.wait()
            print(f"[subprocess] Exit code: {proc.returncode}")

            if self._is_task_cancelled(task):
                raise RuntimeError("Task cancelled")

            return proc.returncode or 0, "\n".join(stderr_lines).encode()
        finally:
            self._running_processes.pop(task.task_id, None)

    async def _process_task(self, task: PackTaskInfo) -> None:
        """
        处理单个打包任务

        根据插件来源选择不同的打包流程：
        - Marketplace 插件：需要先下载插件包
        - 本地插件：直接使用已上传的包

        执行过程中通过 SSE 推送进度事件。

        Args:
            task: 待处理的任务信息
        """
        if self._is_task_cancelled(task):
            return

        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now()
        self._emit_event(
            TaskStartedEvent(
                session_id=task.session_id,
                task_id=task.task_id,
                plugin_name=task.name,
                plugin_version=task.version,
                architecture=task.architecture,
                timestamp=datetime.now(),
            )
        )

        try:
            if task.source == PluginSource.MARKETPLACE:
                await self._pack_marketplace_plugin(task)
            else:
                await self._pack_local_plugin(task)

            if self._is_task_cancelled(task):
                return

            task.status = TaskStatus.SUCCESS
            task.updated_at = datetime.now()
            self._emit_event(
                TaskSuccessEvent(
                    session_id=task.session_id,
                    task_id=task.task_id,
                    plugin_name=task.name,
                    plugin_version=task.version,
                    timestamp=datetime.now(),
                )
            )
        except PackageStepError as e:
            if self._is_task_cancelled(task):
                return
            task.status = TaskStatus.FAILED
            task.current_step = e.step
            task.error_message = e.message
            task.raw_error = e.raw_error
            task.updated_at = datetime.now()
            self._emit_event(
                TaskFailedEvent(
                    session_id=task.session_id,
                    task_id=task.task_id,
                    plugin_name=task.name,
                    step=e.step,
                    message=e.message,
                    raw_error=e.raw_error,
                    timestamp=datetime.now(),
                )
            )

    async def _pack_marketplace_plugin(self, task: PackTaskInfo) -> None:
        """
        打包 Marketplace 插件

        执行完整的打包流程：
        1. 创建任务目录结构
        2. 从 Marketplace 下载插件包
        3. 解析插件依赖
        4. 下载所有依赖包
        5. 生成离线安装包

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 任一步骤失败时抛出
        """
        await self._storage.create_task_dirs(task.task_id)
        if self._is_task_cancelled(task):
            return
        await self._step_download(task)
        if self._is_task_cancelled(task):
            return
        await self._step_resolve_deps(task)
        if self._is_task_cancelled(task):
            return
        await self._step_download_deps(task)
        if self._is_task_cancelled(task):
            return
        await self._step_package(task)

    async def _pack_local_plugin(self, task: PackTaskInfo) -> None:
        """
        打包本地插件

        本地插件跳过下载步骤，直接从已上传的文件开始处理：
        1. 创建任务目录结构
        2. 解析插件依赖
        3. 下载所有依赖包
        4. 生成离线安装包

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 任一步骤失败时抛出
        """
        await self._storage.create_task_dirs(task.task_id)
        if self._is_task_cancelled(task):
            return
        await self._step_resolve_deps(task)
        if self._is_task_cancelled(task):
            return
        await self._step_download_deps(task)
        if self._is_task_cancelled(task):
            return
        await self._step_package(task)

    async def _step_download(self, task: PackTaskInfo) -> None:
        """
        步骤：下载插件包

        从 Dify Marketplace 下载指定版本的插件包（.difypkg 文件）。
        下载的文件保存到任务的 source 目录。

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 下载失败时抛出
        """
        task.current_step = PackStep.DOWNLOADING
        task.step_detail = None
        task.updated_at = datetime.now()
        self._emit_event(
            StepProgressEvent(
                session_id=task.session_id,
                task_id=task.task_id,
                plugin_name=task.name,
                step=PackStep.DOWNLOADING,
                message=STEP_MESSAGES[PackStep.DOWNLOADING],
                timestamp=datetime.now(),
            )
        )

        try:
            response = await self._marketplace.download_plugin(
                author=task.author,
                name=task.name,
                version=task.version,
            )
            filename = f"{task.author}-{task.name}_{task.version}.difypkg"
            await self._storage.save_plugin_package(task.task_id, response.content, filename)
        except Exception as e:
            raise PackageStepError(
                step=PackStep.DOWNLOADING,
                message="下载插件包失败",
                raw_error=str(e),
            ) from None

    async def _step_resolve_deps(self, task: PackTaskInfo) -> None:
        """
        步骤：解析依赖

        解析插件的 Python 依赖：
        1. 解压 .difypkg 文件到 plugin 目录
        2. 检查是否存在 pyproject.toml 或 requirements.txt
        3. 如果只有 pyproject.toml，使用 uv 工具生成 requirements.txt

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 解析失败时抛出
        """
        task.current_step = PackStep.RESOLVING_DEPS
        task.step_detail = None
        task.updated_at = datetime.now()
        self._emit_event(
            StepProgressEvent(
                session_id=task.session_id,
                task_id=task.task_id,
                plugin_name=task.name,
                step=PackStep.RESOLVING_DEPS,
                message=STEP_MESSAGES[PackStep.RESOLVING_DEPS],
                timestamp=datetime.now(),
            )
        )

        source_dir = self._storage.get_source_dir(task.task_id)
        plugin_dir = self._storage.get_plugin_dir(task.task_id)

        difypkg_files = list(source_dir.glob("*.difypkg"))
        if not difypkg_files:
            raise PackageStepError(
                step=PackStep.RESOLVING_DEPS,
                message="插件缺少依赖定义文件",
                raw_error="No .difypkg file found in source directory",
            )

        with zipfile.ZipFile(difypkg_files[0], "r") as zf:
            zf.extractall(plugin_dir)

        has_pyproject = (plugin_dir / "pyproject.toml").exists()
        has_requirements = (plugin_dir / "requirements.txt").exists()

        if has_pyproject and has_requirements:
            return

        if has_pyproject and not has_requirements:
            try:
                returncode, _stdout, stderr = await self._run_subprocess(
                    task,
                    ["uv", "lock"],
                    cwd=str(plugin_dir),
                )
                if returncode != 0:
                    raise PackageStepError(
                        step=PackStep.RESOLVING_DEPS,
                        message="解析依赖失败",
                        raw_error=stderr.decode(),
                    )

                returncode, stdout, stderr = await self._run_subprocess(
                    task,
                    ["uv", "export"],
                    cwd=str(plugin_dir),
                )
                if returncode != 0:
                    raise PackageStepError(
                        step=PackStep.RESOLVING_DEPS,
                        message="解析依赖失败",
                        raw_error=stderr.decode(),
                    )
                (plugin_dir / "requirements.txt").write_bytes(stdout)
            except RuntimeError as e:
                raise PackageStepError(
                    step=PackStep.RESOLVING_DEPS,
                    message="解析依赖失败",
                    raw_error=str(e),
                ) from None
            except PackageStepError:
                raise
            except Exception as e:
                raise PackageStepError(
                    step=PackStep.RESOLVING_DEPS,
                    message="解析依赖失败",
                    raw_error=str(e),
                ) from None

        if not has_pyproject and not has_requirements:
            raise PackageStepError(
                step=PackStep.RESOLVING_DEPS,
                message="插件缺少依赖定义文件",
                raw_error="No pyproject.toml or requirements.txt found",
            )

    async def _step_download_deps(self, task: PackTaskInfo) -> None:
        task.current_step = PackStep.DOWNLOADING_DEPS
        task.step_detail = None
        task.updated_at = datetime.now()

        plugin_dir = self._storage.get_plugin_dir(task.task_id)
        wheels_dir = plugin_dir / "wheels"
        wheels_dir.mkdir(exist_ok=True)

        req_file = plugin_dir / "requirements.txt"
        total_deps = 0
        if req_file.exists():
            total_deps = sum(
                1 for line in req_file.read_text().splitlines()
                if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("-")
            )

        self._emit_event(
            StepProgressEvent(
                session_id=task.session_id,
                task_id=task.task_id,
                plugin_name=task.name,
                step=PackStep.DOWNLOADING_DEPS,
                message=STEP_MESSAGES[PackStep.DOWNLOADING_DEPS],
                detail=f"共 {total_deps} 个依赖包" if total_deps > 0 else None,
                progress={"current": 0, "total": total_deps} if total_deps > 0 else None,
                timestamp=datetime.now(),
            )
        )

        pip_mirror_url = self._settings.PIP_MIRROR_URL

        pip_cmd = self._build_pip_download_cmd(
            task,
            str(plugin_dir / "requirements.txt"),
            str(wheels_dir),
            pip_mirror_url,
        )
        print(f"[pip download] Command: {' '.join(pip_cmd)}")
        print(f"[pip download] Python: {sys.executable}")
        print(f"[pip download] Mirror: {pip_mirror_url}")
        print(f"[pip download] Requirements file: {req_file}")
        print(f"[pip download] Total deps: {total_deps}")
        if req_file.exists():
            print(f"[pip download] Requirements content:\n{req_file.read_text()}")

        processed_count = 0
        last_emit_time = 0.0
        throttle_interval = 0.2

        def on_progress(line: str):
            nonlocal processed_count, last_emit_time

            if "\r" in line:
                line = line.split("\r")[-1]
            line = line.strip()
            if not line:
                return
            print(f"[pip download] {line}")

            detail = None
            should_count = False

            if "Collecting" in line:
                parts = line.split()
                if len(parts) >= 2:
                    package_info = parts[1]
                    detail = f"正在处理: {package_info}"
                    should_count = True
            elif "Downloading" in line:
                parts = line.split()
                filename = ""
                for part in parts:
                    if part.endswith(".whl") or part.endswith(".tar.gz"):
                        filename = part
                        break
                if not filename:
                    if "http" in line or "/" in line:
                        filename = line.split("/")[-1].split("?")[0]
                    else:
                        filename = parts[-1] if parts else line
                detail = f"正在下载: {filename[:50]}"
                should_count = True
            elif "Saved" in line:
                parts = line.split()
                for part in parts:
                    if part.endswith(".whl") or part.endswith(".tar.gz"):
                        detail = f"已保存: {part}"
                        should_count = True
                        break
            else:
                task.step_detail = line[:100]
                task.updated_at = datetime.now()
                now = time.monotonic()
                if now - last_emit_time >= throttle_interval:
                    last_emit_time = now
                    self._emit_event(
                        StepProgressEvent(
                            session_id=task.session_id,
                            task_id=task.task_id,
                            plugin_name=task.name,
                            step=PackStep.DOWNLOADING_DEPS,
                            message=STEP_MESSAGES[PackStep.DOWNLOADING_DEPS],
                            detail=line[:100],
                            progress={"current": processed_count, "total": total_deps} if total_deps > 0 else None,
                            timestamp=datetime.now(),
                        )
                    )
                return

            if should_count:
                processed_count += 1

            progress = {"current": processed_count, "total": total_deps} if total_deps > 0 else None
            if progress and processed_count <= total_deps:
                detail = f"正在下载依赖包 ({processed_count}/{total_deps}): {detail.split(': ', 1)[-1]}"

            task.step_detail = detail
            task.updated_at = datetime.now()

            now = time.monotonic()
            if now - last_emit_time >= throttle_interval:
                last_emit_time = now
                self._emit_event(
                    StepProgressEvent(
                        session_id=task.session_id,
                        task_id=task.task_id,
                        plugin_name=task.name,
                        step=PackStep.DOWNLOADING_DEPS,
                        message=STEP_MESSAGES[PackStep.DOWNLOADING_DEPS],
                        detail=detail,
                        progress=progress,
                        timestamp=datetime.now(),
                    )
                )

        try:
            pip_env = {
                **os.environ,
                "PIP_PROGRESS_BAR": "off",
                "PIP_NO_COLOR": "1",
                "PYTHONUNBUFFERED": "1",
            }
            returncode, stderr = await self._run_subprocess_with_progress(
                task,
                pip_cmd,
                cwd=str(plugin_dir),
                progress_callback=on_progress,
                env=pip_env,
            )
            if returncode != 0:
                raise PackageStepError(
                    step=PackStep.DOWNLOADING_DEPS,
                    message="下载依赖包失败",
                    raw_error=stderr.decode(),
                )
        except RuntimeError:
            return
        except PackageStepError:
            raise
        except Exception as e:
            raise PackageStepError(
                step=PackStep.DOWNLOADING_DEPS,
                message="下载依赖包失败",
                raw_error=str(e),
            ) from None

    async def _step_package(self, task: PackTaskInfo) -> None:
        task.current_step = PackStep.PACKAGING
        task.step_detail = None
        task.updated_at = datetime.now()
        self._emit_event(
            StepProgressEvent(
                session_id=task.session_id,
                task_id=task.task_id,
                plugin_name=task.name,
                step=PackStep.PACKAGING,
                message=STEP_MESSAGES[PackStep.PACKAGING],
                timestamp=datetime.now(),
            )
        )

        plugin_dir = self._storage.get_plugin_dir(task.task_id)
        output_dir = self._storage.get_output_dir(task.task_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        req_file = plugin_dir / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text()
            header = "--no-index\n--find-links=./wheels\n"
            if not content.startswith("--no-index"):
                req_file.write_text(header + content)

        pyproject_file = plugin_dir / "pyproject.toml"
        if pyproject_file.exists():
            content = pyproject_file.read_text()
            if "[tool.uv]" not in content:
                uv_config = '\n[tool.uv]\nno-index = true\nfind-links = ["./wheels"]\nprerelease = "allow"\n'
                pyproject_file.write_text(content + uv_config)

        output_path = output_dir / f"{task.name}-{task.version}-offline.difypkg"

        last_emit_time = 0.0
        throttle_interval = 0.2

        def on_progress(line: str):
            nonlocal last_emit_time
            line = line.strip()
            if not line:
                return
            print(f"[dify-plugin] {line}")
            task.step_detail = line
            task.updated_at = datetime.now()
            now = time.monotonic()
            if now - last_emit_time >= throttle_interval:
                last_emit_time = now
                self._emit_event(
                    StepProgressEvent(
                        session_id=task.session_id,
                        task_id=task.task_id,
                        plugin_name=task.name,
                        step=PackStep.PACKAGING,
                        message=STEP_MESSAGES[PackStep.PACKAGING],
                        detail=line[:100],
                        timestamp=datetime.now(),
                    )
                )

        try:
            returncode, stderr = await self._run_subprocess_with_progress(
                task,
                [
                    self._get_cli_path(task),
                    "plugin",
                    "package",
                    str(plugin_dir),
                    "-o",
                    str(output_path),
                    "--max-size",
                    "5120",
                ],
                progress_callback=on_progress,
            )
            if returncode != 0:
                raise PackageStepError(
                    step=PackStep.PACKAGING,
                    message="打包离线插件失败",
                    raw_error=stderr.decode(),
                )
        except RuntimeError:
            return
        except PackageStepError:
            raise
        except Exception as e:
            raise PackageStepError(
                step=PackStep.PACKAGING,
                message="打包离线插件失败",
                raw_error=str(e),
            ) from None

        task.result_file_path = output_path
        task.updated_at = datetime.now()

    def _build_pip_download_cmd(
        self,
        task: PackTaskInfo,
        req_file_path: str,
        wheels_dir: str,
        pip_mirror_url: str,
    ) -> list[str]:
        trusted_host = pip_mirror_url.split("//")[1].split("/")[0]
        platform = ARCHITECTURE_PLATFORM_MAP[task.architecture]
        return [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--prefer-binary",
            "--timeout", "120",
            "--retries", "3",
            "--platform", platform,
            "--only-binary=:all:",
            "-r", req_file_path,
            "-d", wheels_dir,
            "--index-url", pip_mirror_url,
            "--trusted-host", trusted_host,
        ]

    def _get_cli_path(self, task: PackTaskInfo) -> str:
        return self._settings.get_cli_path(task.architecture)

    def _validate_cli_path(self, task: PackTaskInfo) -> None:
        cli_path = self._get_cli_path(task)
        from pathlib import Path
        if not Path(cli_path).exists():
            raise PackageStepError(
                step=PackStep.PACKAGING,
                message=f"CLI 工具不存在: {cli_path}",
                raw_error=f"CLI tool not found at {cli_path}",
            )

    def _parse_pip_download_error(self, stderr: bytes, architecture: Architecture) -> None:
        error_msg = stderr.decode()
        if "No matching distribution found for" in error_msg:
            import re
            match = re.search(r"No matching distribution found for (\S+)", error_msg)
            package_name = match.group(1) if match else "unknown"
            arch_label = architecture.value
            raise PackageStepError(
                step=PackStep.DOWNLOADING_DEPS,
                message=f"依赖包 {package_name} 不支持 {arch_label} 架构",
                raw_error=error_msg,
            )
        raise PackageStepError(
            step=PackStep.DOWNLOADING_DEPS,
            message="下载依赖包失败",
            raw_error=error_msg,
        )

    def _check_session_completion(self, session_id: str) -> None:
        """
        检查会话是否完成

        当会话中所有任务都处于终态（成功/失败/取消）时，
        标记会话完成并推送完成事件。

        Args:
            session_id: 会话ID
        """
        session = self._sessions.get(session_id)
        if not session:
            return
        tasks = [self._tasks[tid] for tid in session.task_ids]
        all_done = all(t.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED) for t in tasks)
        if all_done:
            session.status = SessionStatus.COMPLETED
            success_count = sum(1 for t in tasks if t.status == TaskStatus.SUCCESS)
            failed_count = sum(1 for t in tasks if t.status in (TaskStatus.FAILED, TaskStatus.CANCELLED))
            self._emit_event(
                SessionCompletedEvent(
                    session_id=session_id,
                    success_count=success_count,
                    failed_count=failed_count,
                    timestamp=datetime.now(),
                )
            )

    def _emit_event(self, event) -> None:
        """
        推送 SSE 事件

        将事件推送给所有订阅该会话的客户端。

        Args:
            event: SSE 事件对象
        """
        subscribers = self._subscribers.get(event.session_id, [])
        for queue in subscribers:
            queue.put_nowait(event)

    def subscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        """
        订阅会话事件

        注册一个队列用于接收该会话的 SSE 事件。

        Args:
            session_id: 会话ID
            queue: 用于接收事件的异步队列
        """
        if session_id not in self._subscribers:
            self._subscribers[session_id] = []
        self._subscribers[session_id].append(queue)

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        """
        取消订阅会话事件

        从订阅列表中移除指定队列。

        Args:
            session_id: 会话ID
            queue: 要移除的队列
        """
        if session_id in self._subscribers:
            self._subscribers[session_id] = [q for q in self._subscribers[session_id] if q is not queue]

    def get_session(self, session_id: str) -> PackSessionInfo | None:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            PackSessionInfo | None: 会话信息，不存在则返回 None
        """
        return self._sessions.get(session_id)

    def get_task(self, task_id: str) -> PackTaskInfo | None:
        """
        获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            PackTaskInfo | None: 任务信息，不存在则返回 None
        """
        return self._tasks.get(task_id)

    async def cancel_session(self, session_id: str) -> bool:
        """
        取消打包会话

        将会话中所有待处理和运行中的任务标记为已取消状态，
        并终止正在运行的子进程。

        Args:
            session_id: 会话ID

        Returns:
            bool: 取消成功返回 True，会话不存在返回 False
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        for task_id in session.task_ids:
            task = self._tasks.get(task_id)
            if task and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                task.updated_at = datetime.now()
                self._terminate_process(task_id)

        session.status = SessionStatus.COMPLETED
        self._emit_event(
            SessionCompletedEvent(
                session_id=session_id,
                success_count=sum(
                    1 for tid in session.task_ids if self._tasks[tid].status == TaskStatus.SUCCESS
                ),
                failed_count=sum(
                    1
                    for tid in session.task_ids
                    if self._tasks[tid].status in (TaskStatus.FAILED, TaskStatus.CANCELLED)
                ),
                timestamp=datetime.now(),
            )
        )
        return True
