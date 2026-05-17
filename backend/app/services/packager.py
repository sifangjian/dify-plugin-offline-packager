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
import uuid
import zipfile
from datetime import datetime

import httpx

from app.core.config import Settings
from app.models.plugin import (
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
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now()
        self._emit_event(
            TaskStartedEvent(
                session_id=task.session_id,
                task_id=task.task_id,
                plugin_name=task.name,
                plugin_version=task.version,
                timestamp=datetime.now(),
            )
        )

        try:
            if task.source == PluginSource.MARKETPLACE:
                await self._pack_marketplace_plugin(task)
            else:
                await self._pack_local_plugin(task)

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
        await self._step_download(task)
        await self._step_resolve_deps(task)
        await self._step_download_deps(task)
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
        await self._step_resolve_deps(task)
        await self._step_download_deps(task)
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
                proc = await asyncio.create_subprocess_exec(
                    "uv",
                    "lock",
                    cwd=str(plugin_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    raise PackageStepError(
                        step=PackStep.RESOLVING_DEPS,
                        message="解析依赖失败",
                        raw_error=stderr.decode(),
                    )

                proc = await asyncio.create_subprocess_exec(
                    "uv",
                    "export",
                    cwd=str(plugin_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    raise PackageStepError(
                        step=PackStep.RESOLVING_DEPS,
                        message="解析依赖失败",
                        raw_error=stderr.decode(),
                    )
                (plugin_dir / "requirements.txt").write_bytes(stdout)
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
        """
        步骤：下载依赖包

        使用 pip download 命令下载所有依赖包到 wheels 目录。
        支持配置 PyPI 镜像源加速下载。
        下载的 wheel 文件将打包进离线安装包。

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 下载失败时抛出
        """
        task.current_step = PackStep.DOWNLOADING_DEPS
        task.updated_at = datetime.now()
        self._emit_event(
            StepProgressEvent(
                session_id=task.session_id,
                task_id=task.task_id,
                plugin_name=task.name,
                step=PackStep.DOWNLOADING_DEPS,
                message=STEP_MESSAGES[PackStep.DOWNLOADING_DEPS],
                timestamp=datetime.now(),
            )
        )

        plugin_dir = self._storage.get_plugin_dir(task.task_id)
        wheels_dir = plugin_dir / "wheels"
        wheels_dir.mkdir(exist_ok=True)

        pip_mirror_url = getattr(self._settings, "PIP_MIRROR_URL", "https://pypi.org/simple")

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3",
                "-m",
                "pip",
                "download",
                "--prefer-binary",
                "-r",
                str(plugin_dir / "requirements.txt"),
                "-d",
                str(wheels_dir),
                "--index-url",
                pip_mirror_url,
                cwd=str(plugin_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise PackageStepError(
                    step=PackStep.DOWNLOADING_DEPS,
                    message="下载依赖包失败",
                    raw_error=stderr.decode(),
                )
        except PackageStepError:
            raise
        except Exception as e:
            raise PackageStepError(
                step=PackStep.DOWNLOADING_DEPS,
                message="下载依赖包失败",
                raw_error=str(e),
            ) from None

    async def _step_package(self, task: PackTaskInfo) -> None:
        """
        步骤：打包离线插件

        使用 Dify Plugin CLI 将插件及其依赖打包成离线安装包：
        1. 修改 requirements.txt，添加离线安装配置
        2. 修改 pyproject.toml，添加 uv 离线配置
        3. 调用 dify-plugin CLI 生成 .difypkg 文件

        生成的离线包可在无网络环境下安装使用。

        Args:
            task: 任务信息

        Raises:
            PackageStepError: 打包失败时抛出
        """
        task.current_step = PackStep.PACKAGING
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

        try:
            proc = await asyncio.create_subprocess_exec(
                self._settings.DIFY_PLUGIN_CLI_PATH,
                "plugin",
                "package",
                str(plugin_dir),
                "-o",
                str(output_path),
                "--max-size",
                "5120",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise PackageStepError(
                    step=PackStep.PACKAGING,
                    message="打包离线插件失败",
                    raw_error=stderr.decode(),
                )
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

        将会话中所有待处理和运行中的任务标记为已取消状态。

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
