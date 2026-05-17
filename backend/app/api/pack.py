"""
打包 API 接口模块

提供插件打包相关的 RESTful API 接口：
- POST /api/v1/plugins/pack: 提交打包请求，支持批量打包多个插件
- POST /api/v1/plugins/cancel/{session_id}: 取消指定的打包会话
- GET /api/v1/plugins/download/{task_id}: 下载打包完成的离线插件包

接口设计遵循异步处理模式：
1. 用户提交打包请求后立即返回 session_id 和 task_id
2. 客户端通过 SSE 订阅打包进度
3. 打包完成后通过下载接口获取结果
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.exceptions import PackageError
from app.models.plugin import PackRequest, PackResponse, PackTaskSummary, TaskStatus
from app.services.packager import PackagerService

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


def get_packager_service(request: Request) -> PackagerService:
    """
    获取打包服务实例

    从应用状态中获取全局打包服务实例。
    该实例在应用启动时初始化，在应用生命周期内共享。

    Args:
        request: FastAPI 请求对象

    Returns:
        PackagerService: 打包服务实例
    """
    return request.app.state.packager_service


_PACKAGER_DEP = Depends(get_packager_service)


@router.post("/pack", response_model=PackResponse)
async def pack_plugins(
    pack_request: PackRequest,
    packager: PackagerService = _PACKAGER_DEP,
):
    """
    提交插件打包请求

    接收待打包的插件列表，创建打包会话和任务，返回任务信息。
    支持批量打包多个插件，每个插件对应一个独立的打包任务。

    请求体示例：
    ```json
    {
        "plugins": [
            {
                "author": "langgenius",
                "name": "agent",
                "version": "0.0.1",
                "source": "marketplace"
            }
        ]
    }
    ```

    Args:
        pack_request: 打包请求，包含待打包的插件列表
        packager: 打包服务实例（依赖注入）

    Returns:
        PackResponse: 包含 session_id 和任务摘要列表的响应

    Note:
        客户端应使用返回的 session_id 通过 SSE 订阅打包进度
    """
    session = await packager.submit_session(pack_request.plugins)

    tasks = []
    for task_id in session.task_ids:
        task = packager.get_task(task_id)
        tasks.append(
            PackTaskSummary(
                task_id=task.task_id,
                author=task.author,
                name=task.name,
                version=task.version,
                status=task.status,
            )
        )

    return PackResponse(session_id=session.session_id, tasks=tasks)


@router.post("/cancel/{session_id}")
async def cancel_session(
    session_id: str,
    packager: PackagerService = _PACKAGER_DEP,
):
    """
    取消打包会话

    取消指定的打包会话，将所有待处理和运行中的任务标记为已取消。
    已完成的任务不受影响。

    Args:
        session_id: 要取消的会话ID
        packager: 打包服务实例（依赖注入）

    Returns:
        dict: 取消成功的确认消息

    Raises:
        PackageError: 会话不存在时抛出 404 错误
    """
    result = await packager.cancel_session(session_id)
    if not result:
        raise PackageError("未找到该打包会话", code="NOT_FOUND", status_code=404)
    return {"message": "已取消"}


@router.get("/download/{task_id}")
async def download_plugin(
    task_id: str,
    packager: PackagerService = _PACKAGER_DEP,
):
    """
    下载打包完成的离线插件包

    下载指定任务的打包结果文件。仅当任务状态为 SUCCESS 时可下载。

    Args:
        task_id: 任务ID
        packager: 打包服务实例（依赖注入）

    Returns:
        StreamingResponse: 文件流响应，包含离线插件包

    Raises:
        PackageError: 任务不存在、任务未完成或文件不存在时抛出相应错误

    Note:
        下载的文件名格式为: {name}-{version}-offline.difypkg
    """
    task = packager.get_task(task_id)
    if not task:
        raise PackageError("未找到该打包任务", code="NOT_FOUND", status_code=404)

    if task.status != TaskStatus.SUCCESS:
        raise PackageError("该任务尚未完成或已失败", code="TASK_NOT_READY", status_code=400)

    if not task.result_file_path or not task.result_file_path.exists():
        raise PackageError("打包结果文件不存在", code="FILE_NOT_FOUND", status_code=404)

    filename = f"{task.name}-{task.version}-offline.difypkg"

    def iterfile():
        """
        文件流生成器

        以 64KB 为单位分块读取文件，适用于大文件下载场景。
        """
        with open(task.result_file_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
