from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, field_validator


class PluginSource(StrEnum):
    MARKETPLACE = "marketplace"
    LOCAL = "local"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PackStep(StrEnum):
    DOWNLOADING = "downloading"
    RESOLVING_DEPS = "resolving_deps"
    DOWNLOADING_DEPS = "downloading_deps"
    PACKAGING = "packaging"


class PackPluginItem(BaseModel):
    author: str
    name: str
    version: str
    source: PluginSource = PluginSource.MARKETPLACE


class PackRequest(BaseModel):
    plugins: list[PackPluginItem]

    @field_validator("plugins")
    @classmethod
    def plugins_must_not_be_empty(cls, v):
        if len(v) == 0:
            raise ValueError("plugins list must not be empty")
        return v


class PackTaskSummary(BaseModel):
    task_id: str
    author: str
    name: str
    version: str
    status: TaskStatus


class PackResponse(BaseModel):
    session_id: str
    tasks: list[PackTaskSummary]


class PackTaskInfo(BaseModel):
    task_id: str
    session_id: str
    author: str
    name: str
    version: str
    source: PluginSource
    local_file_path: Path | None = None
    status: TaskStatus = TaskStatus.PENDING
    current_step: PackStep | None = None
    error_message: str | None = None
    raw_error: str | None = None
    result_file_path: Path | None = None
    created_at: datetime
    updated_at: datetime


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


class PackSessionInfo(BaseModel):
    session_id: str
    task_ids: list[str]
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime
