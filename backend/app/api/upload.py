"""
文件上传 API 接口模块

提供本地插件文件上传功能：
- POST /api/v1/plugins/upload: 上传 .difypkg 文件，解析插件信息

支持批量上传，返回每个文件的解析结果（成功/失败）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.core.config import Settings
from app.models.plugin import BatchUploadResponse, UploadError, UploadResponse
from app.services.plugin_parser import PluginParser
from app.services.storage import StorageService

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


def get_storage_service(request: Request) -> StorageService:
    return request.app.state.storage_service


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


_storage_dep = Depends(get_storage_service)
_settings_dep = Depends(get_settings_dep)


@router.post("/upload", response_model=BatchUploadResponse)
async def upload_plugins(
    files: Annotated[list[UploadFile], File()],
    storage: StorageService = _storage_dep,
    settings: Settings = _settings_dep,
) -> BatchUploadResponse:
    """
    上传本地插件文件

    接收一个或多个 .difypkg 文件，解析每个文件的插件信息。
    支持部分成功部分失败的场景。

    Args:
        files: 上传的文件列表
        storage: 存储服务实例
        settings: 应用配置

    Returns:
        BatchUploadResponse: 包含成功和失败列表的响应
    """
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    success: list[UploadResponse] = []
    failed: list[UploadError] = []

    for file in files:
        if not file.filename:
            failed.append(UploadError(filename="unknown", error="文件名无效"))
            continue

        if not file.filename.endswith(".difypkg"):
            failed.append(UploadError(filename=file.filename, error="文件格式不正确，仅支持 .difypkg 文件"))
            continue

        content = await file.read()
        if len(content) > max_size:
            failed.append(
                UploadError(
                    filename=file.filename,
                    error=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE_MB}MB）",
                )
            )
            continue

        try:
            upload_id, file_path = await storage.save_upload_file(content, file.filename)
            manifest = PluginParser.parse(file_path)

            storage.update_upload_metadata(upload_id, manifest.author, manifest.name, manifest.version)

            success.append(
                UploadResponse(
                    upload_id=upload_id,
                    author=manifest.author,
                    name=manifest.name,
                    version=manifest.version,
                    label=manifest.label,
                    description=manifest.description,
                )
            )
        except ValueError as e:
            failed.append(UploadError(filename=file.filename, error=str(e)))
        except Exception:
            failed.append(UploadError(filename=file.filename, error="无法识别该插件包，请确认文件格式正确"))

    return BatchUploadResponse(success=success, failed=failed)
