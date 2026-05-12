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
    def __init__(self, step: PackStep, message: str, raw_error: str):
        self.step = step
        self.message = message
        self.raw_error = raw_error
        super().__init__(message)


class PackagerService:
    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        settings: Settings,
        storage: StorageService,
    ):
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
        self._consumer_task = asyncio.create_task(self._queue_consumer())

    async def stop(self) -> None:
        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task

    async def submit_session(self, plugins: list[PackPluginItem]) -> PackSessionInfo:
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
        await self._storage.create_task_dirs(task.task_id)
        await self._step_download(task)
        await self._step_resolve_deps(task)
        await self._step_download_deps(task)
        await self._step_package(task)

    async def _pack_local_plugin(self, task: PackTaskInfo) -> None:
        await self._storage.create_task_dirs(task.task_id)
        await self._step_resolve_deps(task)
        await self._step_download_deps(task)
        await self._step_package(task)

    async def _step_download(self, task: PackTaskInfo) -> None:
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
        session = self._sessions.get(session_id)
        if not session:
            return
        tasks = [self._tasks[tid] for tid in session.task_ids]
        all_done = all(t.status in (TaskStatus.SUCCESS, TaskStatus.FAILED) for t in tasks)
        if all_done:
            session.status = SessionStatus.COMPLETED
            success_count = sum(1 for t in tasks if t.status == TaskStatus.SUCCESS)
            failed_count = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
            self._emit_event(
                SessionCompletedEvent(
                    session_id=session_id,
                    success_count=success_count,
                    failed_count=failed_count,
                    timestamp=datetime.now(),
                )
            )

    def _emit_event(self, event) -> None:
        subscribers = self._subscribers.get(event.session_id, [])
        for queue in subscribers:
            queue.put_nowait(event)

    def subscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        if session_id not in self._subscribers:
            self._subscribers[session_id] = []
        self._subscribers[session_id].append(queue)

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        if session_id in self._subscribers:
            self._subscribers[session_id] = [q for q in self._subscribers[session_id] if q is not queue]

    def get_session(self, session_id: str) -> PackSessionInfo | None:
        return self._sessions.get(session_id)

    def get_task(self, task_id: str) -> PackTaskInfo | None:
        return self._tasks.get(task_id)
