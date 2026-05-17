"""
SSE API 接口模块

提供 Server-Sent Events (SSE) 接口，用于实时推送打包进度：
- GET /sse/pack/{session_id}: 订阅打包进度事件

SSE 连接流程：
1. 客户端发起 SSE 请求
2. 服务端推送 session_started 事件
3. 推送每个任务的 task_started 和当前状态
4. 持续推送 step_progress、task_success/failed 事件
5. 推送 session_completed 事件后关闭连接
"""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.core.exceptions import PackageError
from app.models.plugin import PackStep, SessionStatus, TaskStatus
from app.models.sse import (
    STEP_MESSAGES,
    SessionCompletedEvent,
    SessionStartedEvent,
    SSEEventType,
    StepProgressEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    TaskSuccessEvent,
)
from app.services.packager import PackagerService

router = APIRouter(prefix="/sse", tags=["sse"])


def get_packager_service(request: Request) -> PackagerService:
    """
    获取打包服务实例

    从应用状态中获取全局打包服务实例。

    Args:
        request: FastAPI 请求对象

    Returns:
        PackagerService: 打包服务实例
    """
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
            if not task:
                continue

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
                            message=STEP_MESSAGES.get(task.current_step, ""),
                            detail=task.step_detail,
                            timestamp=datetime.now(),
                        ).model_dump(mode="json")
                    ),
                }
            elif task.status == TaskStatus.SUCCESS:
                yield {
                    "event": SSEEventType.TASK_SUCCESS,
                    "data": json.dumps(
                        TaskSuccessEvent(
                            session_id=session_id,
                            task_id=task.task_id,
                            plugin_name=task.name,
                            plugin_version=task.version,
                            timestamp=datetime.now(),
                        ).model_dump(mode="json")
                    ),
                }
            elif task.status == TaskStatus.FAILED:
                yield {
                    "event": SSEEventType.TASK_FAILED,
                    "data": json.dumps(
                        TaskFailedEvent(
                            session_id=session_id,
                            task_id=task.task_id,
                            plugin_name=task.name,
                            step=task.current_step or PackStep.DOWNLOADING,
                            message=task.error_message or "",
                            raw_error=task.raw_error or "",
                            timestamp=datetime.now(),
                        ).model_dump(mode="json")
                    ),
                }

        if session.status == SessionStatus.COMPLETED:
            tasks = [packager.get_task(tid) for tid in session.task_ids]
            success_count = sum(1 for t in tasks if t and t.status == TaskStatus.SUCCESS)
            failed_count = sum(1 for t in tasks if t and t.status in (TaskStatus.FAILED, TaskStatus.CANCELLED))
            yield {
                "event": SSEEventType.SESSION_COMPLETED,
                "data": json.dumps(
                    SessionCompletedEvent(
                        session_id=session_id,
                        success_count=success_count,
                        failed_count=failed_count,
                        timestamp=datetime.now(),
                    ).model_dump(mode="json")
                ),
            }
            return

        while True:
            event = await queue.get()
            yield {
                "event": event.event_type,
                "data": json.dumps(event.model_dump(mode="json")),
            }
            if event.event_type == SSEEventType.SESSION_COMPLETED:
                break
    except asyncio.CancelledError:
        pass
    finally:
        packager.unsubscribe(session_id, queue)


@router.get("/pack/{session_id}")
async def sse_pack_progress(
    session_id: str,
    packager: PackagerService = _PACKAGER_DEP,
):
    """
    订阅打包进度

    建立 SSE 连接，实时接收打包进度事件。

    Args:
        session_id: 会话ID
        packager: 打包服务实例（依赖注入）

    Returns:
        EventSourceResponse: SSE 响应流

    Raises:
        PackageError: 会话不存在时抛出 404 错误

    Note:
        连接会在 session_completed 事件后自动关闭
    """
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
