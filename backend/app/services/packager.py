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
import functools
import logging
import os
import re
import shutil
import stat
import sys
import time
import uuid
import zipfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

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

ARCHITECTURE_PLATFORM_MAP: dict[Architecture, list[str]] = {
    # 支持多种 manylinux 标准，按优先级尝试
    # manylinux_2_28 (2024年标准) - 支持新版本的包
    # manylinux2014 (2014年标准) - 支持旧版本的包
    Architecture.LINUX_AMD64: [
        "manylinux_2_28_x86_64",  # 优先尝试新标准
        "manylinux2014_x86_64",   # 回退到旧标准
    ],
    Architecture.LINUX_ARM64: [
        "manylinux_2_28_aarch64",
        "manylinux2014_aarch64",
    ],
    Architecture.DARWIN_AMD64: ["macosx_11_0_x86_64"],
    Architecture.DARWIN_ARM64: ["macosx_11_0_arm64"],
}

logger = logging.getLogger(__name__)


def check_cancelled(func: Callable) -> Callable:
    """
    装饰器：自动检查任务取消状态
    
    在方法执行前后自动检查任务是否被取消，如果取消则提前返回。
    
    Args:
        func: 需要装饰的异步方法
        
    Returns:
        装饰后的方法
        
    使用示例：
        @check_cancelled
        async def _step_download(self, task: PackTaskInfo):
            # 执行前自动检查取消
            await download_file()
            # 执行后自动检查取消
    """
    @functools.wraps(func)
    async def wrapper(self, task: PackTaskInfo, *args, **kwargs):
        # 执行前检查取消
        if self._is_task_cancelled(task):
            logger.info(f"Task {task.task_id} cancelled before {func.__name__}")
            return
        
        # 执行原方法
        result = await func(self, task, *args, **kwargs)
        
        # 执行后检查取消
        if self._is_task_cancelled(task):
            logger.info(f"Task {task.task_id} cancelled after {func.__name__}")
            return
        
        return result
    
    return wrapper


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
                upload_id=plugin.upload_id,
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
            except Exception as e:
                # 记录未预期的异常
                logger.exception(
                    f"Task {task.task_id} failed with unexpected error: {e}",
                    extra={
                        "task_id": task.task_id,
                        "session_id": task.session_id,
                        "plugin": f"{task.author}/{task.name}@{task.version}",
                    }
                )
                # 更新任务状态为失败
                task.status = TaskStatus.FAILED
                task.error_message = f"未预期的错误: {str(e)}"
                task.raw_error = str(e)
                task.updated_at = datetime.now()
                self._emit_event(
                    TaskFailedEvent(
                        session_id=task.session_id,
                        task_id=task.task_id,
                        plugin_name=task.name,
                        step=task.current_step or PackStep.DOWNLOADING,
                        message=f"任务执行失败: {str(e)}",
                        raw_error=str(e),
                        timestamp=datetime.now(),
                    )
                )
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
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._running_processes[task.task_id] = proc

        try:
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                print(f"[subprocess] 失败 (exit code: {proc.returncode})")
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
                            if progress_callback:
                                progress_callback(line_str)
                    break
                buf += chunk
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    line_str = line_bytes.decode(errors="replace").strip()
                    if line_str:
                        lines.append(line_str)
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
                        if progress_callback:
                            progress_callback(line_str)
                    buf = last_part

        try:
            await asyncio.gather(
                read_stream(proc.stdout, stdout_lines, False),
                read_stream(proc.stderr, stderr_lines, True),
            )
            await proc.wait()

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
        logger.info(
            f"[任务处理] 开始处理任务: {task.task_id}, 插件: {task.author}/{task.name}@{task.version}, 来源: {task.source}",
            extra={
                "task_id": task.task_id,
                "session_id": task.session_id,
                "plugin": f"{task.author}/{task.name}@{task.version}",
                "source": task.source.value,
                "architecture": task.architecture.value,
            }
        )

        if self._is_task_cancelled(task):
            logger.info(f"[任务处理] 任务已取消: {task.task_id}")
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
            # 关键分支：根据插件来源选择打包流程
            if task.source == PluginSource.MARKETPLACE:
                logger.info(
                    f"[任务处理] 插件来源为 Marketplace，执行在线打包流程",
                    extra={"task_id": task.task_id, "source": "marketplace"}
                )
                await self._pack_marketplace_plugin(task)
            else:
                logger.info(
                    f"[任务处理] 插件来源为本地文件，执行本地打包流程",
                    extra={"task_id": task.task_id, "source": "local", "upload_id": task.upload_id}
                )
                await self._pack_local_plugin(task)

            if self._is_task_cancelled(task):
                logger.info(f"[任务处理] 任务在打包完成后被取消: {task.task_id}")
                return

            # 任务成功完成
            logger.info(
                f"[任务处理] 任务执行成功: {task.task_id}, 插件: {task.author}/{task.name}@{task.version}",
                extra={
                    "task_id": task.task_id,
                    "session_id": task.session_id,
                    "plugin": f"{task.author}/{task.name}@{task.version}",
                }
            )
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
            # 打包步骤错误：已知的业务错误
            if self._is_task_cancelled(task):
                logger.info(f"[任务处理] 任务在步骤错误后被取消: {task.task_id}")
                return
            logger.error(
                f"[任务处理] 任务在步骤 {e.step} 失败: {e.message}",
                extra={
                    "task_id": task.task_id,
                    "session_id": task.session_id,
                    "plugin": f"{task.author}/{task.name}@{task.version}",
                    "step": e.step.value if hasattr(e.step, 'value') else str(e.step),
                    "error_message": e.message,
                    "raw_error": e.raw_error,
                }
            )
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
        except asyncio.CancelledError:
            # 任务被取消：向上抛出让 _queue_consumer 处理
            logger.info(
                f"[任务处理] 任务被取消 (CancelledError): {task.task_id}",
                extra={"task_id": task.task_id, "plugin": f"{task.author}/{task.name}@{task.version}"}
            )
            raise
        except Exception as e:
            # 未预期的错误：记录日志并向上抛出
            logger.exception(
                f"[任务处理] 任务遇到未预期的错误: {task.task_id}, 错误类型: {type(e).__name__}, 错误信息: {e}",
                extra={
                    "task_id": task.task_id,
                    "session_id": task.session_id,
                    "plugin": f"{task.author}/{task.name}@{task.version}",
                    "error_type": type(e).__name__,
                }
            )
            raise

    @check_cancelled
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
        await self._step_download(task)
        await self._step_resolve_deps(task)
        await self._step_download_deps(task)
        await self._step_package(task)

    @check_cancelled
    async def _pack_local_plugin(self, task: PackTaskInfo) -> None:
        """
        打包本地插件

        本地插件跳过下载步骤，直接从已上传的文件开始处理：
        1. 创建任务目录结构
        2. 从上传目录复制文件到 source 目录
        3. 解析插件依赖
        4. 下载所有依赖包
        5. 生成离线安装包

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 任一步骤失败时抛出
        """
        await self._storage.create_task_dirs(task.task_id)

        if not task.upload_id:
            raise PackageStepError(
                step=PackStep.DOWNLOADING,
                message="本地插件缺少 upload_id",
                raw_error="Missing upload_id for local plugin",
            )

        local_file = self._storage.get_upload_file(task.upload_id)
        if not local_file:
            raise PackageStepError(
                step=PackStep.DOWNLOADING,
                message="上传文件已过期，请重新上传",
                raw_error=f"Upload file expired or not found: {task.upload_id}",
            )

        source_dir = self._storage.get_source_dir(task.task_id)
        dest_file = source_dir / f"{task.author}-{task.name}_{task.version}.difypkg"
        shutil.copy2(local_file, dest_file)

        await self._step_resolve_deps(task)
        await self._step_download_deps(task)
        await self._step_package(task)

    @check_cancelled
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

    @check_cancelled
    async def _step_resolve_deps(self, task: PackTaskInfo) -> None:
        """
        步骤：解析依赖

        解析插件的 Python 依赖：
        1. 解压 .difypkg 文件到 plugin 目录
        2. 检查是否存在 pyproject.toml 或 requirements.txt
        3. 如果只有 pyproject.toml，使用 uv 工具生成 requirements.txt
        4. 对 requirements.txt 进行版本兼容性处理，替换不存在的版本

        依赖解析分支说明：
        - 场景1: 同时有 pyproject.toml 和 requirements.txt → 直接使用 requirements.txt
        - 场景2: 只有 pyproject.toml → 使用 uv lock + uv export 生成 requirements.txt
        - 场景3: 只有 requirements.txt → 直接使用
        - 场景4: 两者都没有 → 抛出错误

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 解析失败时抛出
        """
        logger.info(
            f"[依赖解析] 开始解析依赖: {task.task_id}",
            extra={"task_id": task.task_id, "plugin": f"{task.author}/{task.name}@{task.version}"}
        )

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

        # 查找并解压 .difypkg 文件
        difypkg_files = list(source_dir.glob("*.difypkg"))
        if not difypkg_files:
            logger.error(
                f"[依赖解析] 未找到 .difypkg 文件: {source_dir}",
                extra={"task_id": task.task_id, "source_dir": str(source_dir)}
            )
            raise PackageStepError(
                step=PackStep.RESOLVING_DEPS,
                message="插件缺少依赖定义文件",
                raw_error="No .difypkg file found in source directory",
            )

        logger.info(
            f"[依赖解析] 找到 .difypkg 文件: {difypkg_files[0].name}, 开始解压",
            extra={"task_id": task.task_id, "difypkg_file": difypkg_files[0].name}
        )
        with zipfile.ZipFile(difypkg_files[0], "r") as zf:
            zf.extractall(plugin_dir)

        # 检查依赖文件存在情况（关键分支判断）
        has_pyproject = (plugin_dir / "pyproject.toml").exists()
        has_requirements = (plugin_dir / "requirements.txt").exists()
        logger.info(
            f"[依赖解析] 检查依赖文件: pyproject.toml={has_pyproject}, requirements.txt={has_requirements}",
            extra={
                "task_id": task.task_id,
                "plugin": f"{task.author}/{task.name}@{task.version}",
                "has_pyproject": has_pyproject,
                "has_requirements": has_requirements,
            }
        )

        # ========== 场景1: 两者都有 ==========
        if has_pyproject and has_requirements:
            logger.info(
                "[依赖解析] 场景1: pyproject.toml 和 requirements.txt 同时存在，直接对 requirements.txt 进行版本兼容性处理",
                extra={"task_id": task.task_id, "scenario": "both_files"},
            )
            req_file = plugin_dir / "requirements.txt"
            # 过滤掉平台特定依赖
            self._filter_platform_specific_deps(req_file)
            self._patch_requirements(req_file)
            logger.info(
                "[依赖解析] 版本兼容性处理完成",
                extra={"task_id": task.task_id},
            )
            return

        # ========== 场景2: 只有 pyproject.toml ==========
        if has_pyproject and not has_requirements:
            logger.info(
                "[依赖解析] 场景2: 只有 pyproject.toml，使用 uv 生成 requirements.txt",
                extra={"task_id": task.task_id, "scenario": "pyproject_only"},
            )
            try:
                logger.info(
                    "[依赖解析] 执行 uv lock 生成锁文件",
                    extra={"task_id": task.task_id, "cwd": str(plugin_dir)}
                )
                returncode, _stdout, stderr = await self._run_subprocess(
                    task,
                    ["uv", "lock"],
                    cwd=str(plugin_dir),
                )
                if returncode != 0:
                    logger.error(
                        f"[依赖解析] uv lock 失败，返回码: {returncode}",
                        extra={"task_id": task.task_id, "stderr": stderr.decode()},
                    )
                    raise PackageStepError(
                        step=PackStep.RESOLVING_DEPS,
                        message="解析依赖失败",
                        raw_error=stderr.decode(),
                    )
                logger.info(
                    "[依赖解析] uv lock 成功，执行 uv export 导出 requirements.txt",
                    extra={"task_id": task.task_id}
                )

                # uv export 参数说明：
                # --no-dev: 不包含开发依赖
                # --no-hashes: 不包含 hash 值（减少文件大小）
                # --all-extras: 包含所有 extras（可选依赖）
                returncode, stdout, stderr = await self._run_subprocess(
                    task,
                    ["uv", "export", "--no-dev", "--no-hashes"],
                    cwd=str(plugin_dir),
                )
                if returncode != 0:
                    logger.error(
                        f"[依赖解析] uv export 失败，返回码: {returncode}",
                        extra={"task_id": task.task_id, "stderr": stderr.decode()},
                    )
                    raise PackageStepError(
                        step=PackStep.RESOLVING_DEPS,
                        message="解析依赖失败",
                        raw_error=stderr.decode(),
                    )
                (plugin_dir / "requirements.txt").write_bytes(stdout)
                logger.info(
                    "[依赖解析] uv export 成功，requirements.txt 已生成",
                    extra={"task_id": task.task_id, "requirements_size": len(stdout)},
                )

                # 过滤掉 Windows 专用依赖，避免在 Linux 打包时导致 uv sync 失败
                self._filter_platform_specific_deps(plugin_dir / "requirements.txt")
                logger.info(
                    "[依赖解析] 已过滤平台特定依赖",
                    extra={"task_id": task.task_id},
                )
                # 应用版本兼容性处理
                req_file = plugin_dir / "requirements.txt"
                self._patch_requirements(req_file)
                logger.info(
                    "[依赖解析] 版本兼容性处理完成",
                    extra={"task_id": task.task_id},
                )
            except RuntimeError as e:
                logger.error(
                    f"[依赖解析] RuntimeError: {e}",
                    extra={"task_id": task.task_id, "error": str(e)},
                )
                raise PackageStepError(
                    step=PackStep.RESOLVING_DEPS,
                    message="解析依赖失败",
                    raw_error=str(e),
                ) from None
            except PackageStepError:
                raise
            except Exception as e:
                logger.error(
                    f"[依赖解析] 未预期的异常: {type(e).__name__}: {e}",
                    extra={"task_id": task.task_id, "error_type": type(e).__name__, "error": str(e)},
                )
                raise PackageStepError(
                    step=PackStep.RESOLVING_DEPS,
                    message="解析依赖失败",
                    raw_error=str(e),
                ) from None

        # ========== 场景3: 只有 requirements.txt ==========
        if not has_pyproject and has_requirements:
            logger.info(
                "[依赖解析] 场景3: 只有 requirements.txt（没有 pyproject.toml），直接进行版本兼容性处理",
                extra={"task_id": task.task_id, "scenario": "requirements_only"},
            )
            req_file = plugin_dir / "requirements.txt"
            # 过滤掉平台特定依赖
            self._filter_platform_specific_deps(req_file)
            self._patch_requirements(req_file)
            logger.info(
                "[依赖解析] 版本兼容性处理完成",
                extra={"task_id": task.task_id},
            )
            return

        # ========== 场景4: 两者都没有 ==========
        logger.error(
            "[依赖解析] 场景4: 缺少依赖定义文件，既没有 pyproject.toml 也没有 requirements.txt",
            extra={"task_id": task.task_id, "plugin_dir": str(plugin_dir), "scenario": "no_files"},
        )
        raise PackageStepError(
            step=PackStep.RESOLVING_DEPS,
            message="插件缺少依赖定义文件",
            raw_error="No pyproject.toml or requirements.txt found",
        )

    def _patch_requirements(self, req_file_path: Path) -> None:
        """
        对 requirements.txt 进行版本兼容性处理

        当前功能：
        1. 移除已知不兼容的依赖包（从 DEPENDENCY_REMOVAL_LIST）

        注意：
        - 版本替换功能暂时禁用（DEPENDENCY_VERSION_PATCHES 已清空）
        - 版本兼容性问题将在下载依赖后通过动态版本同步解决
        - _sync_requirements_with_wheels 和 _sync_pyproject_with_wheels 会根据实际下载的版本更新

        Args:
            req_file_path: requirements.txt 文件路径
        """
        if not req_file_path.exists():
            return

        removal_list = self._settings.DEPENDENCY_REMOVAL_LIST
        content = req_file_path.read_text()
        content = re.sub(r"\\\n\s+", " ", content)  # 处理续行符
        lines = content.splitlines()
        patched_lines = []

        for line in lines:
            stripped = line.strip()

            # 跳过空行、注释、特殊指令
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                patched_lines.append(line)
                continue

            # 解析依赖行
            match = re.match(
                r"^([A-Za-z0-9_.-]+(?:\[.*?\])?)\s*(~=|==|!=|<=|>=|<|>|===)\s*([^\s;]+)",
                stripped,
            )
            if not match:
                patched_lines.append(line)
                continue

            pkg_name_with_extras = match.group(1)
            pkg_name_lower = pkg_name_with_extras.lower()
            pkg_name_no_extras = re.sub(r"\[.*?\]", "", pkg_name_with_extras).lower()

            # 检查是否需要移除
            should_remove = False
            for remove_pkg in removal_list:
                rp_lower = remove_pkg.lower()
                if pkg_name_lower == rp_lower or pkg_name_no_extras == rp_lower:
                    should_remove = True
                    logger.info(
                        f"[版本兼容性] 移除不兼容的包: {pkg_name_with_extras}",
                        extra={"package": pkg_name_with_extras, "reason": "在移除列表中"},
                    )
                    break

            if should_remove:
                continue  # 移除这个包

            # 版本替换功能暂时禁用
            # 当前策略：依赖动态版本同步（在下载依赖后根据实际下载的版本更新）
            # patches = self._settings.DEPENDENCY_VERSION_PATCHES
            # if patches:
            #     operator = match.group(2)
            #     version = match.group(3).strip()
            #     version_key = f"{operator}{version}"
            #     replacement = None
            #     if pkg_name_lower in patches and version_key in patches[pkg_name_lower]:
            #         replacement = patches[pkg_name_lower][version_key]
            #     elif pkg_name_no_extras in patches and version_key in patches[pkg_name_no_extras]:
            #         replacement = patches[pkg_name_no_extras][version_key]
            #     if replacement:
            #         result = re.sub(re.escape(f"{pkg_name_with_extras}{operator}{version}"), replacement, stripped, count=1)
            #         result = re.sub(r"\s*--hash=\S+", "", result)
            #         patched_lines.append(result)
            #         continue

            # 保留原始行（移除 hash 信息）
            result = re.sub(r"\s*--hash=\S+", "", stripped)
            patched_lines.append(result)

        req_file_path.write_text("\n".join(patched_lines) + "\n")

    def _filter_platform_specific_deps(self, req_file_path: Path) -> None:
        """
        过滤掉平台特定的依赖（如 Windows 专用依赖）

        当在 Linux 上打包时，移除 Windows 专用的依赖，避免在 uv sync 时因缺少这些依赖而失败。

        Args:
            req_file_path: requirements.txt 文件路径
        """
        if not req_file_path.exists():
            return

        content = req_file_path.read_text()
        lines = content.splitlines()
        filtered_lines = []
        removed_count = 0

        for line in lines:
            stripped = line.strip()

            # 跳过空行、注释
            if not stripped or stripped.startswith("#"):
                filtered_lines.append(line)
                continue

            # 检查是否包含 Windows 专用的环境标记
            # 例如：cffi==2.0.0 ; sys_platform == 'win32'
            # 例如：colorama==0.4.6 ; sys_platform == 'win32'
            if ";" in line:
                line_lower = line.lower()
                # 检查是否是 Windows 专用依赖
                if "win32" in line_lower or "windows" in line_lower:
                    # 提取包名用于日志
                    match = re.match(r"^([A-Za-z0-9_.-]+)", stripped)
                    pkg_name = match.group(1) if match else "unknown"
                    logger.info(
                        f"[依赖过滤] 移除 Windows 专用依赖: {pkg_name}",
                        extra={"package": pkg_name, "line": stripped},
                    )
                    removed_count += 1
                    continue

            filtered_lines.append(line)

        if removed_count > 0:
            req_file_path.write_text("\n".join(filtered_lines) + "\n")
            logger.info(
                f"[依赖过滤] 共移除 {removed_count} 个平台特定依赖",
                extra={"removed_count": removed_count},
            )
            print(f"[依赖过滤] 移除了 {removed_count} 个 Windows 专用依赖")

    def _sync_requirements_with_wheels(self, req_file_path: Path, wheels_dir: Path) -> None:
        """
        根据实际下载的 wheel 文件同步更新 requirements.txt 中的版本要求

        当 pip download 下载了替代版本的 wheel 文件时，需要更新 requirements.txt
        以确保版本要求与实际下载的版本一致，避免安装时版本不匹配。

        同时，移除未下载的依赖（如平台特定依赖），确保 requirements.txt 与实际下载的包完全一致。

        Args:
            req_file_path: requirements.txt 文件路径
            wheels_dir: wheels 目录路径
        """
        if not req_file_path.exists() or not wheels_dir.exists():
            return

        # 解析 wheels 目录中的所有 wheel 文件，构建包名到版本的映射
        # wheel 文件名格式：{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
        wheel_versions: dict[str, str] = {}
        for wheel_file in wheels_dir.glob("*.whl"):
            filename = wheel_file.name
            # 解析 wheel 文件名
            # 格式：package-version-py3-none-any.whl 或 package-version-build-py3-none-any.whl
            parts = filename.rsplit(".", 1)[0].split("-")  # 移除 .whl 扩展名
            if len(parts) >= 5:
                # 最后 3 部分是 python-abi-platform
                # 第一部分是包名，第二部分是版本（可能有 build tag）
                pkg_name = parts[0].lower()
                version = parts[1]
                # 标准化包名（将 _ 替换为 -）
                pkg_name_normalized = pkg_name.replace("_", "-")
                wheel_versions[pkg_name_normalized] = version
                # 同时保存原始名称（带下划线）
                if "_" in pkg_name:
                    wheel_versions[pkg_name] = version

        if not wheel_versions:
            print(f"[同步版本] wheels 目录为空")
            return

        print(f"[同步版本] 找到 {len(wheel_versions)} 个包")

        # 读取并更新 requirements.txt
        content = req_file_path.read_text()
        content = re.sub(r"\\\n\s+", " ", content)  # 处理续行
        lines = content.splitlines()
        updated_lines = []
        updated_count = 0
        removed_count = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                updated_lines.append(line)
                continue

            # 解析依赖行
            # 格式：package[extras]==version 或 package[extras]>=version 等
            match = re.match(
                r"^([A-Za-z0-9_.-]+(?:\[.*?\])?)\s*(~=|==|!=|<=|>=|<|>|===)\s*([^\s;]+)",
                stripped,
            )
            if not match:
                updated_lines.append(line)
                continue

            pkg_name_with_extras = match.group(1)
            operator = match.group(2)
            original_version = match.group(3).strip()
            pkg_name_no_extras = re.sub(r"\[.*?\]", "", pkg_name_with_extras)
            pkg_name_lower = pkg_name_no_extras.lower()
            pkg_name_normalized = pkg_name_lower.replace("_", "-")

            # 查找实际下载的版本
            actual_version = wheel_versions.get(pkg_name_normalized) or wheel_versions.get(pkg_name_lower)

            if actual_version:
                # 包已下载
                if actual_version != original_version:
                    # 版本不匹配，更新为实际下载的版本
                    # 移除 hash 信息
                    new_line = re.sub(
                        re.escape(f"{pkg_name_with_extras}{operator}{original_version}"),
                        f"{pkg_name_with_extras}=={actual_version}",
                        stripped,
                        count=1,
                    )
                    new_line = re.sub(r"\s*--hash=\S+", "", new_line)
                    updated_lines.append(new_line)
                    updated_count += 1
                else:
                    # 版本匹配，保留原始行（移除 hash 信息）
                    new_line = re.sub(r"\s*--hash=\S+", "", stripped)
                    updated_lines.append(new_line)
            else:
                # 包未下载，移除这一行
                logger.info(
                    f"[同步版本] 移除未下载的依赖: {pkg_name_no_extras}",
                    extra={"package": pkg_name_no_extras, "line": stripped},
                )
                removed_count += 1

        if updated_count > 0 or removed_count > 0:
            req_file_path.write_text("\n".join(updated_lines) + "\n")
            print(f"[同步版本] 更新了 {updated_count} 个包的版本，移除了 {removed_count} 个未下载的包 (requirements.txt)")
        else:
            print(f"[同步版本] 所有版本匹配，无需更新 (requirements.txt)")

    def _sync_pyproject_with_wheels(self, pyproject_file_path: Path, wheels_dir: Path) -> None:
        """
        根据实际下载的 wheel 文件同步更新 pyproject.toml 中的版本要求

        当 pip download 下载了替代版本的 wheel 文件时，需要更新 pyproject.toml
        以确保版本要求与实际下载的版本一致，避免 uv sync 时版本不匹配。

        Args:
            pyproject_file_path: pyproject.toml 文件路径
            wheels_dir: wheels 目录路径
        """
        if not pyproject_file_path.exists() or not wheels_dir.exists():
            return

        # 解析 wheels 目录中的所有 wheel 文件，构建包名到版本的映射
        wheel_versions: dict[str, str] = {}
        for wheel_file in wheels_dir.glob("*.whl"):
            filename = wheel_file.name
            parts = filename.rsplit(".", 1)[0].split("-")
            if len(parts) >= 5:
                pkg_name = parts[0].lower()
                version = parts[1]
                pkg_name_normalized = pkg_name.replace("_", "-")
                wheel_versions[pkg_name_normalized] = version
                if "_" in pkg_name:
                    wheel_versions[pkg_name] = version

        if not wheel_versions:
            return

        # 读取并更新 pyproject.toml
        content = pyproject_file_path.read_text()
        lines = content.splitlines()
        updated_lines = []
        updated_count = 0
        in_dependencies = False

        for line in lines:
            stripped = line.strip()

            # 检测 dependencies 数组的开始和结束
            if stripped.startswith("dependencies") and "=" in stripped and "[" in stripped:
                in_dependencies = True
                updated_lines.append(line)
                continue

            if in_dependencies:
                if stripped == "]":
                    in_dependencies = False
                    updated_lines.append(line)
                    continue

                # 解析依赖行
                # 格式："package==version" 或 "package>=version" 等
                match = re.match(
                    r'^"([A-Za-z0-9_.-]+(?:\[.*?\])?)\s*(~=|==|!=|<=|>=|<|>|===)\s*([^\s;"]+)"',
                    stripped,
                )
                if match:
                    pkg_name_with_extras = match.group(1)
                    operator = match.group(2)
                    original_version = match.group(3).strip()
                    pkg_name_no_extras = re.sub(r"\[.*?\]", "", pkg_name_with_extras)
                    pkg_name_lower = pkg_name_no_extras.lower()
                    pkg_name_normalized = pkg_name_lower.replace("_", "-")

                    # 查找实际下载的版本
                    actual_version = wheel_versions.get(pkg_name_normalized) or wheel_versions.get(pkg_name_lower)

                    if actual_version and actual_version != original_version:
                        # 版本不匹配，更新为实际下载的版本
                        new_line = re.sub(
                            re.escape(f"{pkg_name_with_extras}{operator}{original_version}"),
                            f"{pkg_name_with_extras}=={actual_version}",
                            line,
                            count=1,
                        )
                        updated_lines.append(new_line)
                        updated_count += 1
                        continue

            updated_lines.append(line)

        if updated_count > 0:
            pyproject_file_path.write_text("\n".join(updated_lines) + "\n")
            print(f"[同步版本] 更新了 {updated_count} 个包的版本 (pyproject.toml)")
        else:
            print(f"[同步版本] 所有版本匹配，无需更新 (pyproject.toml)")

    @check_cancelled
    async def _step_download_deps(self, task: PackTaskInfo) -> None:
        """
        步骤：下载依赖包

        使用 pip download 下载所有依赖包到 wheels 目录。
        下载完成后同步 requirements.txt 和 pyproject.toml 中的版本信息。

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 下载失败时抛出
        """
        logger.info(
            f"[下载依赖] 开始下载依赖: {task.task_id}",
            extra={
                "task_id": task.task_id,
                "plugin": f"{task.author}/{task.name}@{task.version}",
                "architecture": task.architecture.value,
            }
        )

        task.current_step = PackStep.DOWNLOADING_DEPS
        task.step_detail = None
        task.updated_at = datetime.now()

        plugin_dir = self._storage.get_plugin_dir(task.task_id)
        wheels_dir = plugin_dir / "wheels"
        wheels_dir.mkdir(exist_ok=True)

        req_file = plugin_dir / "requirements.txt"
        total_deps = 0
        if req_file.exists():
            req_content = req_file.read_text()
            total_deps = sum(
                1
                for line in req_content.splitlines()
                if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("-")
            )
            logger.info(
                f"[下载依赖] requirements.txt 存在，共 {total_deps} 个依赖包",
                extra={"task_id": task.task_id, "total_deps": total_deps, "req_file": str(req_file)},
            )
            # 打印 requirements.txt 内容（调试用）
            print(f"[下载依赖] requirements.txt 内容:")
            for line in req_content.splitlines()[:20]:  # 只显示前 20 行
                if line.strip() and not line.strip().startswith("#"):
                    print(f"  {line}")
            if len(req_content.splitlines()) > 20:
                print(f"  ... 还有 {len(req_content.splitlines()) - 20} 行")
        else:
            logger.warning(
                f"[下载依赖] requirements.txt 不存在: {req_file}",
                extra={"task_id": task.task_id, "req_file": str(req_file)},
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

        # 然后使用 pip download 下载
        # 这样可以使用 uv 的 PubGrub 算法（与 Dify 一致）
        pip_mirror_url = self._settings.PIP_MIRROR_URL

        # 获取平台列表，按优先级尝试
        platforms = ARCHITECTURE_PLATFORM_MAP[task.architecture]
        # 如果是字符串，转换为列表（向后兼容）
        if isinstance(platforms, str):
            platforms = [platforms]

        logger.info(
            f"[下载依赖] 配置信息: pip_mirror={pip_mirror_url}, platforms={platforms}",
            extra={
                "task_id": task.task_id,
                "pip_mirror_url": pip_mirror_url,
                "platforms": platforms,
                "wheels_dir": str(wheels_dir),
            }
        )

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

            # 只显示关键信息，过滤冗余输出
            if any(keyword in line for keyword in ["Collecting", "Downloading", "Saved", "ERROR", "Successfully"]):
                # 简化输出
                if "Collecting" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        print(f"  → {parts[1]}")
                elif "Saved" in line:
                    parts = line.split()
                    for part in parts:
                        if part.endswith(".whl") or part.endswith(".tar.gz"):
                            print(f"  ✓ {part}")
                            break
                elif "ERROR" in line:
                    print(f"  ✗ {line}")
                elif "Successfully" in line:
                    print(f"  ✓ {line}")

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

            # 使用 pip download 下载依赖
            # requirements.txt 已在 _step_resolve_deps 中通过 uv export 生成，版本已锁定
            print(f"[下载] 使用 pip download 下载依赖...")

            download_cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--prefer-binary",
                "--timeout",
                "120",
                "--retries",
                "3",
                "-r",
                str(req_file),
                "-d",
                str(wheels_dir),
                "--index-url",
                pip_mirror_url,
            ]

            returncode, stderr = await self._run_subprocess_with_progress(
                task,
                download_cmd,
                cwd=str(plugin_dir),
                progress_callback=on_progress,
                env=pip_env,
            )

            if returncode == 0:
                logger.info(
                    f"[下载依赖] pip download 完成，开始检查依赖完整性",
                    extra={"task_id": task.task_id, "total_deps": total_deps},
                )
                print(f"[下载] ✓ pip download 完成")

                # 检查是否所有依赖都下载成功
                if not self._check_all_deps_downloaded(req_file, wheels_dir):
                    missing_count = self._count_missing_deps(req_file, wheels_dir)
                    logger.error(
                        f"[下载依赖] 依赖完整性检查失败，缺少 {missing_count} 个包",
                        extra={"task_id": task.task_id, "missing_count": missing_count},
                    )

                    # 打印 wheels 目录内容（调试用）
                    print(f"[调试] wheels 目录内容:")
                    for wheel_file in sorted(wheels_dir.glob("*.whl"))[:20]:
                        print(f"  {wheel_file.name}")
                    wheel_count = len(list(wheels_dir.glob("*.whl")))
                    if wheel_count > 20:
                        print(f"  ... 还有 {wheel_count - 20} 个文件")

                    raise PackageStepError(
                        step=PackStep.DOWNLOADING_DEPS,
                        message=f"部分依赖包下载失败，缺少 {missing_count} 个包",
                        raw_error="Dependency integrity check failed. Some packages were not downloaded.",
                    )

                logger.info(
                    f"[下载依赖] 依赖完整性检查通过，开始同步版本信息",
                    extra={"task_id": task.task_id},
                )
                print(f"[下载] ✓ 依赖完整性检查通过")

                # 同步版本
                self._sync_requirements_with_wheels(req_file, wheels_dir)
                pyproject_file = plugin_dir / "pyproject.toml"
                if pyproject_file.exists():
                    self._sync_pyproject_with_wheels(pyproject_file, wheels_dir)
                logger.info(
                    f"[下载依赖] 版本同步完成",
                    extra={"task_id": task.task_id},
                )
            else:
                error_msg = stderr.decode()
                logger.error(
                    f"[下载依赖] pip download 失败，返回码: {returncode}",
                    extra={
                        "task_id": task.task_id,
                        "returncode": returncode,
                        "stderr": error_msg[:1000],  # 限制日志长度
                    },
                )
                raise PackageStepError(
                    step=PackStep.DOWNLOADING_DEPS,
                    message="下载依赖包失败",
                    raw_error=error_msg,
                )
        except RuntimeError as e:
            logger.warning(
                f"[下载依赖] RuntimeError (可能是任务被取消): {e}",
                extra={"task_id": task.task_id, "error": str(e)},
            )
            return
        except PackageStepError:
            raise
        except Exception as e:
            logger.error(
                f"[下载依赖] 未预期的异常: {type(e).__name__}: {e}",
                extra={"task_id": task.task_id, "error_type": type(e).__name__, "error": str(e)},
            )
            raise PackageStepError(
                step=PackStep.DOWNLOADING_DEPS,
                message="下载依赖包失败",
                raw_error=str(e),
            ) from None

        # 版本同步已在下载过程中实时完成，这里不需要再次同步

    @check_cancelled
    async def _step_package(self, task: PackTaskInfo) -> None:
        """
        步骤：打包离线插件

        使用 dify-plugin CLI 工具将插件和依赖打包成离线安装包。
        打包前会配置 uv 的 flat index 以使用本地 wheels 目录。

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 打包失败时抛出
        """
        logger.info(
            f"[打包] 开始打包离线插件: {task.task_id}",
            extra={
                "task_id": task.task_id,
                "plugin": f"{task.author}/{task.name}@{task.version}",
                "architecture": task.architecture.value,
            }
        )

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

        # 根据架构确定目标平台
        target_platform = "linux"
        if task.architecture.value.startswith("darwin"):
            target_platform = "macos"

        # 为 uv 配置本地 wheels 目录作为 flat index
        # 这相当于 pip 的 --find-links
        # 关键：设置 default = true，确保 uv 只使用本地 wheels，不尝试访问 PyPI
        # 这样在离线环境中，如果 wheels 目录包含所有依赖，就不会尝试联网
        pyproject_file = plugin_dir / "pyproject.toml"
        if pyproject_file.exists():
            logger.info(
                f"[打包] pyproject.toml 存在，添加 uv flat index 配置（离线模式）",
                extra={"task_id": task.task_id, "pyproject_file": str(pyproject_file)},
            )
            content = pyproject_file.read_text()

            # 添加 [tool.uv] 配置，指定目标平台
            # 这样 uv 在解析依赖时会排除其他平台的依赖
            uv_config = f'''
[tool.uv]
# 指定目标平台，避免解析 Windows 专用依赖
python-platform = "{target_platform}"
'''

            # 添加 [[tool.uv.index]] 配置，使用 flat index
            # 这相当于 pip 的 --find-links ./wheels
            # default = true 表示这是默认索引，uv 不会尝试访问 PyPI
            uv_index_config = '''
[[tool.uv.index]]
name = "local-wheels"
url = "./wheels"
format = "flat"
default = true
'''
            pyproject_file.write_text(content + uv_config + uv_index_config)
            logger.info(
                f"[打包] 已添加 uv 离线配置 (platform={target_platform}, default=true)",
                extra={"task_id": task.task_id, "target_platform": target_platform},
            )
            print(f"[配置] 添加了 uv 离线配置（平台: {target_platform}）")
        else:
            logger.info(
                f"[打包] pyproject.toml 不存在，跳过 uv 配置",
                extra={"task_id": task.task_id},
            )

        # 保留 uv.lock，但添加 python-platform 配置
        # uv.lock 包含了所有平台的依赖，但 uv sync 在安装时会根据 python-platform 配置来选择依赖
        # 如果 python-platform = "linux"，uv 会忽略 Windows 专用依赖
        uv_lock_file = plugin_dir / "uv.lock"
        if uv_lock_file.exists():
            logger.info(
                f"[打包] 保留 uv.lock，uv 将使用 python-platform={target_platform} 配置",
                extra={"task_id": task.task_id, "uv_lock_file": str(uv_lock_file), "target_platform": target_platform},
            )
            print(f"[配置] 保留 uv.lock，uv 将使用平台配置: {target_platform}")
        else:
            logger.warning(
                f"[打包] uv.lock 文件不存在，uv 将根据 pyproject.toml 解析依赖",
                extra={"task_id": task.task_id},
            )
            print(f"[警告] uv.lock 不存在，uv 将根据 pyproject.toml 解析依赖")

        output_path = output_dir / f"{task.name}-{task.version}-{task.architecture.value}-offline.difypkg"
        cli_path = self._get_cli_path(task)
        logger.info(
            f"[打包] 打包配置: cli_path={cli_path}, output_path={output_path}",
            extra={
                "task_id": task.task_id,
                "cli_path": cli_path,
                "output_path": str(output_path),
                "plugin_dir": str(plugin_dir),
            }
        )

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
                error_msg = stderr.decode()
                logger.error(
                    f"[打包] dify-plugin package 失败，返回码: {returncode}",
                    extra={
                        "task_id": task.task_id,
                        "returncode": returncode,
                        "stderr": error_msg[:1000],  # 限制日志长度
                    },
                )
                raise PackageStepError(
                    step=PackStep.PACKAGING,
                    message="打包离线插件失败",
                    raw_error=error_msg,
                )

            # 打包成功
            logger.info(
                f"[打包] 离线插件打包成功: {output_path}",
                extra={
                    "task_id": task.task_id,
                    "output_path": str(output_path),
                    "file_size": output_path.stat().st_size if output_path.exists() else 0,
                },
            )
        except RuntimeError as e:
            logger.warning(
                f"[打包] RuntimeError (可能是任务被取消): {e}",
                extra={"task_id": task.task_id, "error": str(e)},
            )
            return
        except PackageStepError:
            raise
        except Exception as e:
            logger.error(
                f"[打包] 未预期的异常: {type(e).__name__}: {e}",
                extra={"task_id": task.task_id, "error_type": type(e).__name__, "error": str(e)},
            )
            raise PackageStepError(
                step=PackStep.PACKAGING,
                message="打包离线插件失败",
                raw_error=str(e),
            ) from None

        task.result_file_path = output_path
        task.updated_at = datetime.now()
        logger.info(
            f"[打包] 任务完成，结果文件: {output_path}",
            extra={"task_id": task.task_id, "result_file": str(output_path)},
        )

    def _parse_failed_packages(self, error_msg: str) -> set[str]:
        """
        解析 pip download 错误信息，提取失败的包名

        Args:
            error_msg: pip download 的错误输出

        Returns:
            失败的包名集合
        """
        failed = set()

        # 匹配 "Could not find a version that satisfies the requirement package==version"
        pattern1 = r"Could not find a version that satisfies the requirement ([^\s]+)"
        for match in re.finditer(pattern1, error_msg):
            pkg_spec = match.group(1)
            # 提取包名（移除版本说明符）
            pkg_name = re.split(r"[=<>~!]", pkg_spec)[0]
            failed.add(pkg_name)

        # 匹配 "No matching distribution found for package==version"
        pattern2 = r"No matching distribution found for ([^\s]+)"
        for match in re.finditer(pattern2, error_msg):
            pkg_spec = match.group(1)
            pkg_name = re.split(r"[=<>~!]", pkg_spec)[0]
            failed.add(pkg_name)

        return failed

    async def _retry_failed_packages(
        self,
        task: PackTaskInfo,
        failed_packages: set[str],
        wheels_dir: str,
        pip_mirror_url: str,
        platform: str,
        progress_callback,
        pip_env: dict,
        plugin_dir: Path,
    ) -> set[str]:
        """
        单独重试失败的包

        Args:
            task: 任务信息
            failed_packages: 失败的包集合
            wheels_dir: wheels 目录
            pip_mirror_url: PyPI 镜像 URL
            platform: 平台标识
            progress_callback: 进度回调
            pip_env: 环境变量
            plugin_dir: 插件目录

        Returns:
            成功下载的包集合
        """
        success_packages = set()
        trusted_host = pip_mirror_url.split("//")[1].split("/")[0]

        for pkg_name in failed_packages:
            # 构建单独下载命令
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--prefer-binary",
                "--timeout",
                "120",
                "--retries",
                "3",
                "--platform",
                platform,
                "--only-binary=:all:",
                pkg_name,
                "-d",
                wheels_dir,
                "--index-url",
                pip_mirror_url,
                "--trusted-host",
                trusted_host,
                "--no-deps",  # 不下载依赖，避免重复
            ]

            try:
                returncode, stderr = await self._run_subprocess_with_progress(
                    task,
                    cmd,
                    cwd=str(plugin_dir),
                    progress_callback=progress_callback,
                    env=pip_env,
                )

                if returncode == 0:
                    print(f"  ✓ {pkg_name}")
                    success_packages.add(pkg_name)
            except Exception:
                pass  # 静默失败，继续尝试下一个包

        return success_packages

    async def _retry_failed_packages_no_platform(
        self,
        task: PackTaskInfo,
        failed_packages: set[str],
        wheels_dir: str,
        pip_mirror_url: str,
        progress_callback,
        pip_env: dict,
        plugin_dir: Path,
    ) -> set[str]:
        """
        不使用平台限制重试失败的包

        Args:
            task: 任务信息
            failed_packages: 失败的包集合
            wheels_dir: wheels 目录
            pip_mirror_url: PyPI 镜像 URL
            progress_callback: 进度回调
            pip_env: 环境变量
            plugin_dir: 插件目录

        Returns:
            成功下载的包集合
        """
        success_packages = set()
        trusted_host = pip_mirror_url.split("//")[1].split("/")[0]

        for pkg_name in failed_packages:
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--prefer-binary",
                "--timeout",
                "120",
                "--retries",
                "3",
                pkg_name,
                "-d",
                wheels_dir,
                "--index-url",
                pip_mirror_url,
                "--trusted-host",
                trusted_host,
                "--no-deps",
            ]

            try:
                returncode, stderr = await self._run_subprocess_with_progress(
                    task,
                    cmd,
                    cwd=str(plugin_dir),
                    progress_callback=progress_callback,
                    env=pip_env,
                )

                if returncode == 0:
                    print(f"  ✓ {pkg_name} (无平台限制)")
                    success_packages.add(pkg_name)
            except Exception:
                pass  # 静默失败，继续尝试下一个包

        return success_packages

    def _check_all_deps_downloaded(self, req_file: Path, wheels_dir: Path) -> bool:
        """
        检查是否所有依赖都已下载到 wheels 目录

        Args:
            req_file: requirements.txt 文件路径
            wheels_dir: wheels 目录路径

        Returns:
            是否所有依赖都已下载
        """
        # 解析 requirements.txt 中的包名
        required_packages = set()
        content = req_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # 处理环境标记（environment markers）
            # 格式：package==version ; condition
            # 例如：cffi==2.0.0 ; sys_platform == 'win32'
            # 如果有环境标记且不满足当前环境，跳过这个依赖
            if ";" in line:
                # 简单处理：检查是否包含 win32 或 Windows 相关的条件
                # 如果是 Windows 专用依赖，在 Linux 上跳过
                line_lower = line.lower()
                if "win32" in line_lower or "windows" in line_lower:
                    # 跳过 Windows 专用依赖
                    continue
                # 其他环境标记（如 platform_python_implementation）暂时忽略
                # 因为在打包时我们无法确定目标环境的 Python 实现

            # 提取包名（移除版本说明符和 extras）
            match = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if match:
                pkg_name = match.group(1).lower().replace("-", "_")
                required_packages.add(pkg_name)

        logger.info(
            f"[依赖检查] requirements.txt 中共有 {len(required_packages)} 个依赖包（已过滤平台特定依赖）",
            extra={"total_required": len(required_packages)},
        )

        # 获取 wheels 目录中已有的包名
        downloaded_packages = set()
        for wheel_file in wheels_dir.glob("*.whl"):
            # wheel 文件名格式: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
            parts = wheel_file.name.split("-")
            if parts:
                pkg_name = parts[0].lower().replace("-", "_")
                downloaded_packages.add(pkg_name)

        logger.info(
            f"[依赖检查] wheels 目录中共有 {len(downloaded_packages)} 个已下载的包",
            extra={"total_downloaded": len(downloaded_packages)},
        )

        # 检查是否所有要求的包都已下载
        missing_packages = required_packages - downloaded_packages
        if missing_packages:
            sorted_missing = sorted(missing_packages)
            logger.error(
                f"[依赖检查] 缺少 {len(missing_packages)} 个包: {', '.join(sorted_missing)}",
                extra={
                    "missing_count": len(missing_packages),
                    "missing_packages": sorted_missing,
                },
            )
            print(f"[检查] 缺少 {len(missing_packages)} 个包: {', '.join(sorted_missing[:10])}")
            if len(sorted_missing) > 10:
                print(f"[检查] ... 还有 {len(sorted_missing) - 10} 个包未显示")
            return False

        return True

    def _count_missing_deps(self, req_file: Path, wheels_dir: Path) -> int:
        """
        统计缺失的依赖包数量

        Args:
            req_file: requirements.txt 文件路径
            wheels_dir: wheels 目录路径

        Returns:
            缺失的包数量
        """
        # 解析 requirements.txt 中的包名
        required_packages = set()
        content = req_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # 处理环境标记（与 _check_all_deps_downloaded 保持一致）
            if ";" in line:
                line_lower = line.lower()
                if "win32" in line_lower or "windows" in line_lower:
                    continue

            match = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if match:
                pkg_name = match.group(1).lower().replace("-", "_")
                required_packages.add(pkg_name)

        # 获取 wheels 目录中已有的包名
        downloaded_packages = set()
        for wheel_file in wheels_dir.glob("*.whl"):
            parts = wheel_file.name.split("-")
            if parts:
                pkg_name = parts[0].lower().replace("-", "_")
                downloaded_packages.add(pkg_name)

        missing_packages = required_packages - downloaded_packages
        return len(missing_packages)

    def _build_pip_download_cmd(
        self,
        task: PackTaskInfo,
        req_file_path: str,
        wheels_dir: str,
        pip_mirror_url: str,
        platform: str | None = None,
    ) -> list[str]:
        trusted_host = pip_mirror_url.split("//")[1].split("/")[0]
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--prefer-binary",
            "--timeout",
            "120",
            "--retries",
            "3",
        ]
        if platform:
            cmd.extend(["--platform", platform, "--only-binary=:all:"])
        cmd.extend([
            "-r",
            req_file_path,
            "-d",
            wheels_dir,
            "--index-url",
            pip_mirror_url,
            "--trusted-host",
            trusted_host,
        ])
        return cmd

    def _build_pip_download_cmd_no_platform(
        self,
        req_file_path: str,
        wheels_dir: str,
        pip_mirror_url: str,
    ) -> list[str]:
        trusted_host = pip_mirror_url.split("//")[1].split("/")[0]
        return [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--prefer-binary",
            "--timeout",
            "120",
            "--retries",
            "3",
            "-r",
            req_file_path,
            "-d",
            wheels_dir,
            "--index-url",
            pip_mirror_url,
            "--trusted-host",
            trusted_host,
        ]

    def _get_cli_path(self, task: PackTaskInfo) -> str:
        cli_path = self._settings.get_cli_path(task.architecture)
        path = Path(cli_path)
        if path.exists() and not os.access(str(path), os.X_OK):
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return cli_path

    def _validate_cli_path(self, task: PackTaskInfo) -> None:
        cli_path = self._get_cli_path(task)
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
                success_count=sum(1 for tid in session.task_ids if self._tasks[tid].status == TaskStatus.SUCCESS),
                failed_count=sum(
                    1
                    for tid in session.task_ids
                    if self._tasks[tid].status in (TaskStatus.FAILED, TaskStatus.CANCELLED)
                ),
                timestamp=datetime.now(),
            )
        )
        return True
