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
from pathlib import Path

import aiofiles


class StorageService:
    """
    存储服务类

    管理打包任务的文件系统操作，包括目录创建、文件存储和清理。

    Attributes:
        _work_dir: 工作目录根路径
    """

    def __init__(self, work_dir: Path):
        """
        初始化存储服务

        Args:
            work_dir: 工作目录根路径，所有任务文件将存储在此目录下
        """
        self._work_dir = work_dir.resolve()

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
