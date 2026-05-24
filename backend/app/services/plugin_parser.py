"""
插件解析服务模块

从 .difypkg 文件中解析 manifest.yaml，提取插件名称、作者、版本等元数据。
.difypkg 文件本质上是 zip 格式，内部包含 manifest.yaml 文件。
"""

import zipfile
from pathlib import Path

import yaml

from app.models.plugin import I18nText, PluginManifest


class PluginParser:
    """插件包解析器"""

    MANIFEST_FILE = "manifest.yaml"

    @classmethod
    def parse(cls, file_path: Path) -> PluginManifest:
        """
        从 .difypkg 文件中解析插件元数据

        Args:
            file_path: 插件包文件路径

        Returns:
            PluginManifest: 解析出的插件元数据

        Raises:
            ValueError: 文件不存在、格式不正确或缺少必要字段
        """
        if not file_path.exists():
            raise ValueError("文件不存在")

        if not zipfile.is_zipfile(file_path):
            raise ValueError("无法识别该插件包，请确认文件格式正确")

        with zipfile.ZipFile(file_path, "r") as zf:
            if cls.MANIFEST_FILE not in zf.namelist():
                raise ValueError("无法识别该插件包，请确认文件格式正确")

            with zf.open(cls.MANIFEST_FILE) as manifest_file:
                content = manifest_file.read().decode("utf-8")
                data = yaml.safe_load(content)

                if not data:
                    raise ValueError("无法识别该插件包，请确认文件格式正确")

                required_fields = ["version", "author", "name"]
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f"插件缺少必要字段: {field}")

                label = data.get("label", {})
                description = data.get("description", {})

                return PluginManifest(
                    version=str(data["version"]),
                    author=str(data["author"]),
                    name=str(data["name"]),
                    label=I18nText(
                        en_US=str(label.get("en_US", "")),
                        zh_Hans=str(label.get("zh_Hans", "")),
                    ),
                    description=I18nText(
                        en_US=str(description.get("en_US", "")),
                        zh_Hans=str(description.get("zh_Hans", "")),
                    ),
                    type=str(data.get("type", "plugin")),
                    icon=str(data.get("icon", "")),
                )
