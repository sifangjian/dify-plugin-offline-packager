import shutil
from pathlib import Path

import aiofiles


class StorageService:
    def __init__(self, work_dir: Path):
        self._work_dir = work_dir

    async def create_task_dirs(self, task_id: str) -> Path:
        task_dir = self._work_dir / task_id
        (task_dir / "source").mkdir(parents=True, exist_ok=True)
        (task_dir / "plugin").mkdir(parents=True, exist_ok=True)
        (task_dir / "output").mkdir(parents=True, exist_ok=True)
        return task_dir

    def get_task_dir(self, task_id: str) -> Path:
        return self._work_dir / task_id

    def get_source_dir(self, task_id: str) -> Path:
        return self._work_dir / task_id / "source"

    def get_plugin_dir(self, task_id: str) -> Path:
        return self._work_dir / task_id / "plugin"

    def get_output_dir(self, task_id: str) -> Path:
        return self._work_dir / task_id / "output"

    async def save_plugin_package(self, task_id: str, content: bytes, filename: str) -> Path:
        source_dir = self.get_source_dir(task_id)
        safe_name = Path(filename).name
        file_path = source_dir / safe_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        return file_path

    def get_result_file(self, task_id: str) -> Path | None:
        output_dir = self.get_output_dir(task_id)
        if output_dir.exists():
            files = list(output_dir.glob("*.difypkg"))
            return files[0] if files else None
        return None

    async def cleanup_task(self, task_id: str) -> None:
        task_dir = self.get_task_dir(task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir)
