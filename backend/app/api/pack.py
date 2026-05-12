from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.exceptions import PackageError
from app.models.plugin import PackRequest, PackResponse, PackTaskSummary, TaskStatus
from app.services.packager import PackagerService

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


def get_packager_service(request: Request) -> PackagerService:
    return request.app.state.packager_service


_PACKAGER_DEP = Depends(get_packager_service)


@router.post("/pack", response_model=PackResponse)
async def pack_plugins(
    pack_request: PackRequest,
    packager: PackagerService = _PACKAGER_DEP,
):
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


@router.get("/download/{task_id}")
async def download_plugin(
    task_id: str,
    packager: PackagerService = _PACKAGER_DEP,
):
    task = packager.get_task(task_id)
    if not task:
        raise PackageError("未找到该打包任务", code="NOT_FOUND", status_code=404)

    if task.status != TaskStatus.SUCCESS:
        raise PackageError("该任务尚未完成或已失败", code="TASK_NOT_READY", status_code=400)

    if not task.result_file_path or not task.result_file_path.exists():
        raise PackageError("打包结果文件不存在", code="FILE_NOT_FOUND", status_code=404)

    filename = f"{task.name}-{task.version}-offline.difypkg"

    def iterfile():
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
