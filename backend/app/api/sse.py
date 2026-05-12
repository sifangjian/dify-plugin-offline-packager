import asyncio
import json

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.core.exceptions import PackageError
from app.models.plugin import TaskStatus
from app.models.sse import SessionStartedEvent, SSEEventType, StepProgressEvent, TaskStartedEvent
from app.services.packager import PackagerService

router = APIRouter(prefix="/sse", tags=["sse"])


def get_packager_service(request: Request) -> PackagerService:
    return request.app.state.packager_service


_PACKAGER_DEP = Depends(get_packager_service)


async def _event_generator(session_id: str, packager: PackagerService):
    from datetime import datetime

    session = packager.get_session(session_id)
    if not session:
        raise PackageError("未找到该打包任务", code="NOT_FOUND", status_code=404)

    queue: asyncio.Queue = asyncio.Queue()
    packager.subscribe(session_id, queue)

    try:
        yield {
            "event": SSEEventType.SESSION_STARTED,
            "data": json.dumps(
                SessionStartedEvent(
                    session_id=session_id,
                    total=len(session.task_ids),
                    timestamp=datetime.now(),
                ).model_dump(mode="json")
            ),
        }

        for task_id in session.task_ids:
            task = packager.get_task(task_id)
            if task:
                yield {
                    "event": SSEEventType.TASK_STARTED,
                    "data": json.dumps(
                        TaskStartedEvent(
                            session_id=session_id,
                            task_id=task.task_id,
                            plugin_name=task.name,
                            plugin_version=task.version,
                            timestamp=datetime.now(),
                        ).model_dump(mode="json")
                    ),
                }
                if task.status == TaskStatus.RUNNING and task.current_step:
                    yield {
                        "event": SSEEventType.STEP_PROGRESS,
                        "data": json.dumps(
                            StepProgressEvent(
                                session_id=session_id,
                                task_id=task.task_id,
                                plugin_name=task.name,
                                step=task.current_step,
                                message="",
                                timestamp=datetime.now(),
                            ).model_dump(mode="json")
                        ),
                    }

        while True:
            event = await queue.get()
            yield {
                "event": event.event_type,
                "data": json.dumps(event.model_dump(mode="json")),
            }
            if event.event_type == SSEEventType.SESSION_COMPLETED:
                break
    finally:
        packager.unsubscribe(session_id, queue)


@router.get("/pack/{session_id}")
async def sse_pack_progress(
    session_id: str,
    packager: PackagerService = _PACKAGER_DEP,
):
    session = packager.get_session(session_id)
    if not session:
        raise PackageError("未找到该打包任务", code="NOT_FOUND", status_code=404)

    return EventSourceResponse(
        _event_generator(session_id, packager),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
