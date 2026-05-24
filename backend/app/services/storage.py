"""
存储服务模块

提供文件系统操作服务，管理打包过程中的文件存储：
- 任务目录管理：创建、获取、清理任务相关目录
- 插件包存储：保存下载的插件包文件
- 结果文件管理：获取打包生成的离线包

目录结构：
workspace/
└── {task_id}/
    ├── source/     # 原始插件包存放目录
    ├── plugin/     # 解压后的插件内容目录
    │   └── wheels/ # 下载的依赖包目录
    └── output/     # 打包结果输出目录
"""

import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles

from app.models.plugin import UploadedFileInfo


class StorageService:
    """
    存储服务类

    管理打包任务的文件系统操作，包括目录创建、文件存储和清理。

    Attributes:
        _work_dir: 工作目录根路径
    """

    def __init__(self, work_dir: Path, upload_expire_hours: int = 24):
        """
        初始化存储服务

        Args:
            work_dir: 工作目录根路径，所有任务文件将存储在此目录下
            upload_expire_hours: 上传文件过期时间（小时）
        """
        self._work_dir = work_dir.resolve()
        self._upload_expire_hours = upload_expire_hours
        self._uploads: dict[str, UploadedFileInfo] = {}

    async def create_task_dirs(self, task_id: str) -> Path:
        """
        创建任务目录结构

        为指定任务创建完整的目录结构，包括：
        - source: 存放原始插件包
        - plugin: 存放解压后的插件内容
        - output: 存放打包结果

        Args:
            task_id: 任务ID

        Returns:
            Path: 任务根目录路径
        """
        task_dir = self._work_dir / task_id
        (task_dir / "source").mkdir(parents=True, exist_ok=True)
        (task_dir / "plugin").mkdir(parents=True, exist_ok=True)
        (task_dir / "output").mkdir(parents=True, exist_ok=True)
        return task_dir

    def get_task_dir(self, task_id: str) -> Path:
        """
        获取任务根目录

        Args:
            task_id: 任务ID

        Returns:
            Path: 任务根目录路径
        """
        return self._work_dir / task_id

    def get_source_dir(self, task_id: str) -> Path:
        """
        获取源文件目录

        源文件目录用于存放从 Marketplace 下载的原始插件包。

        Args:
            task_id: 任务ID

        Returns:
            Path: 源文件目录路径
        """
        return self._work_dir / task_id / "source"

    def get_plugin_dir(self, task_id: str) -> Path:
        """
        获取插件目录

        插件目录用于存放解压后的插件内容，包括：
        - 插件源代码
        - pyproject.toml / requirements.txt
        - wheels/ 子目录存放依赖包

        Args:
            task_id: 任务ID

        Returns:
            Path: 插件目录路径
        """
        return self._work_dir / task_id / "plugin"

    def get_output_dir(self, task_id: str) -> Path:
        """
        获取输出目录

        输出目录用于存放打包生成的离线插件包。

        Args:
            task_id: 任务ID

        Returns:
            Path: 输出目录路径
        """
        return self._work_dir / task_id / "output"

    async def save_plugin_package(self, task_id: str, content: bytes, filename: str) -> Path:
        """
        保存插件包文件

        将下载的插件包二进制内容保存到源文件目录。

        Args:
            task_id: 任务ID
            content: 插件包二进制内容
            filename: 文件名

        Returns:
            Path: 保存后的文件路径

        Note:
            文件名会进行安全处理，只保留基本文件名，防止路径遍历攻击
        """
        source_dir = self.get_source_dir(task_id)
        safe_name = Path(filename).name
        file_path = source_dir / safe_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        return file_path

    def get_result_file(self, task_id: str) -> Path | None:
        """
        获取结果文件

        查找并返回输出目录中的打包结果文件。

        Args:
            task_id: 任务ID

        Returns:
            Path | None: 结果文件路径，不存在则返回 None
        """
        output_dir = self.get_output_dir(task_id)
        if output_dir.exists():
            files = list(output_dir.glob("*.difypkg"))
            return files[0] if files else None
        return None

    async def cleanup_task(self, task_id: str) -> None:
        """
        清理任务目录

        删除指定任务的所有文件和目录，释放磁盘空间。
        应在任务完成且结果已下载后调用。

        Args:
            task_id: 任务ID
        """
        task_dir = self.get_task_dir(task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir)

    async def save_upload_file(self, content: bytes, filename: str) -> tuple[str, Path]:
        """
        保存上传的插件文件

        Args:
            content: 文件二进制内容
            filename: 原始文件名

        Returns:
            tuple[str, Path]: (upload_id, 文件保存路径)
        """
        upload_id = str(uuid.uuid4())
        upload_dir = self._work_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(filename).name
        file_path = upload_dir / f"{upload_id}_{safe_name}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        now = datetime.now()
        self._uploads[upload_id] = UploadedFileInfo(
            upload_id=upload_id,
            file_path=file_path,
            author="",
            name="",
            version="",
            created_at=now,
            expires_at=now + timedelta(hours=self._upload_expire_hours),
        )

        return upload_id, file_path

    def get_upload_file(self, upload_id: str) -> Path | None:
        """
        获取上传文件路径

        检查文件是否存在且未过期。

        Args:
            upload_id: 上传ID

        Returns:
            Path | None: 文件路径，过期或不存在返回 None
        """
        info = self._uploads.get(upload_id)
        if not info:
            return None
        if datetime.now() > info.expires_at:
            return None
        if not info.file_path.exists():
            return None
        return info.file_path

    def get_upload_info(self, upload_id: str) -> UploadedFileInfo | None:
        """
        获取上传文件信息

        Args:
            upload_id: 上传ID

        Returns:
            UploadedFileInfo | None: 上传文件信息
        """
        return self._uploads.get(upload_id)

    def update_upload_metadata(self, upload_id: str, author: str, name: str, version: str) -> None:
        """
        更新上传文件的元数据

        Args:
            upload_id: 上传ID
            author: 插件作者
            name: 插件名称
            version: 插件版本
        """
        info = self._uploads.get(upload_id)
        if info:
            info.author = author
            info.name = name
            info.version = version

    def remove_upload(self, upload_id: str) -> None:
        """
        删除上传文件

        Args:
            upload_id: 上传ID
        """
        info = self._uploads.pop(upload_id, None)
        if info and info.file_path.exists():
            info.file_path.unlink()

    async def cleanup_expired_uploads(self) -> int:
        """
        清理所有过期的上传文件

        Returns:
            int: 清理的文件数量
        """
        now = datetime.now()
        expired = [upload_id for upload_id, info in self._uploads.items() if now > info.expires_at]
        for upload_id in expired:
            self.remove_upload(upload_id)
        return len(expired)
