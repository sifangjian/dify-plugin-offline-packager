"""
SSE 事件模型模块

定义 Server-Sent Events (SSE) 相关的数据模型，用于实时推送打包进度：
- 事件类型枚举：SSEEventType
- 步骤消息映射：STEP_MESSAGES
- 事件基类：SSEEvent
- 具体事件类型：SessionStartedEvent、TaskStartedEvent 等

事件流程：
session_started → task_started → step_progress* → task_success/failed → session_completed
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.models.plugin import PackStep


class SSEEventType(StrEnum):
    """
    SSE 事件类型枚举

    定义所有可能的 SSE 事件类型：
    - SESSION_STARTED: 会话开始，包含任务总数
    - TASK_STARTED: 任务开始处理
    - STEP_PROGRESS: 步骤进度更新
    - TASK_SUCCESS: 任务成功完成
    - TASK_FAILED: 任务失败
    - SESSION_COMPLETED: 会话完成，包含成功/失败统计
    """

    SESSION_STARTED = "session_started"
    TASK_STARTED = "task_started"
    STEP_PROGRESS = "step_progress"
    TASK_SUCCESS = "task_success"
    TASK_FAILED = "task_failed"
    SESSION_COMPLETED = "session_completed"

"""
    步骤消息映射

    为每个打包步骤提供用户友好的中文描述消息。
"""
STEP_MESSAGES: dict[PackStep, str] = {
    PackStep.DOWNLOADING: "正在下载插件包...",
    PackStep.RESOLVING_DEPS: "正在解析依赖...",
    PackStep.DOWNLOADING_DEPS: "正在下载依赖包...",
    PackStep.PACKAGING: "正在打包离线插件...",
}


class SSEEvent(BaseModel):
    """
    SSE 事件基类

    所有 SSE 事件的基类，定义通用字段。

    Attributes:
        event_type: 事件类型
        session_id: 所属会话ID
        timestamp: 事件时间戳
    """

    event_type: SSEEventType
    session_id: str
    timestamp: datetime


class SessionStartedEvent(SSEEvent):
    """
    会话开始事件

    当打包会话开始时推送，告知客户端本次会话包含的任务总数。

    Attributes:
        total: 任务总数
    """

    event_type: SSEEventType = SSEEventType.SESSION_STARTED
    total: int


class TaskStartedEvent(SSEEvent):
    """
    任务开始事件

    当某个打包任务开始处理时推送。

    Attributes:
        task_id: 任务ID
        plugin_name: 插件名称
        plugin_version: 插件版本
    """

    event_type: SSEEventType = SSEEventType.TASK_STARTED
    task_id: str
    plugin_name: str
    plugin_version: str


class StepProgressEvent(SSEEvent):
    """
    步骤进度事件

    当打包任务进入新步骤时推送，用于更新前端进度显示。

    Attributes:
        task_id: 任务ID
        plugin_name: 插件名称
        step: 当前步骤
        message: 步骤描述消息
        detail: 详细进度信息（如正在下载的包名）
    """

    event_type: SSEEventType = SSEEventType.STEP_PROGRESS
    task_id: str
    plugin_name: str
    step: PackStep
    message: str
    detail: str | None = None


class TaskSuccessEvent(SSEEvent):
    """
    任务成功事件

    当打包任务成功完成时推送。

    Attributes:
        task_id: 任务ID
        plugin_name: 插件名称
        plugin_version: 插件版本
    """

    event_type: SSEEventType = SSEEventType.TASK_SUCCESS
    task_id: str
    plugin_name: str
    plugin_version: str


class TaskFailedEvent(SSEEvent):
    """
    任务失败事件

    当打包任务失败时推送，包含错误详情。

    Attributes:
        task_id: 任务ID
        plugin_name: 插件名称
        step: 失败时的步骤
        message: 错误消息
        raw_error: 原始错误详情
    """

    event_type: SSEEventType = SSEEventType.TASK_FAILED
    task_id: str
    plugin_name: str
    step: PackStep
    message: str
    raw_error: str


class SessionCompletedEvent(SSEEvent):
    """
    会话完成事件

    当打包会话中所有任务都完成时推送，包含统计信息。
    客户端收到此事件后应关闭 SSE 连接。

    Attributes:
        success_count: 成功任务数
        failed_count: 失败任务数（包含取消的任务）
    """

    event_type: SSEEventType = SSEEventType.SESSION_COMPLETED
    success_count: int
    failed_count: int
