from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.models.plugin import PackStep


class SSEEventType(StrEnum):
    SESSION_STARTED = "session_started"
    TASK_STARTED = "task_started"
    STEP_PROGRESS = "step_progress"
    TASK_SUCCESS = "task_success"
    TASK_FAILED = "task_failed"
    SESSION_COMPLETED = "session_completed"


STEP_MESSAGES: dict[PackStep, str] = {
    PackStep.DOWNLOADING: "正在下载插件包...",
    PackStep.RESOLVING_DEPS: "正在解析依赖...",
    PackStep.DOWNLOADING_DEPS: "正在下载依赖包...",
    PackStep.PACKAGING: "正在打包离线插件...",
}


class SSEEvent(BaseModel):
    event_type: SSEEventType
    session_id: str
    timestamp: datetime


class SessionStartedEvent(SSEEvent):
    event_type: SSEEventType = SSEEventType.SESSION_STARTED
    total: int


class TaskStartedEvent(SSEEvent):
    event_type: SSEEventType = SSEEventType.TASK_STARTED
    task_id: str
    plugin_name: str
    plugin_version: str


class StepProgressEvent(SSEEvent):
    event_type: SSEEventType = SSEEventType.STEP_PROGRESS
    task_id: str
    plugin_name: str
    step: PackStep
    message: str


class TaskSuccessEvent(SSEEvent):
    event_type: SSEEventType = SSEEventType.TASK_SUCCESS
    task_id: str
    plugin_name: str
    plugin_version: str


class TaskFailedEvent(SSEEvent):
    event_type: SSEEventType = SSEEventType.TASK_FAILED
    task_id: str
    plugin_name: str
    step: PackStep
    message: str
    raw_error: str


class SessionCompletedEvent(SSEEvent):
    event_type: SSEEventType = SSEEventType.SESSION_COMPLETED
    success_count: int
    failed_count: int
