"""
插件数据模型模块

定义插件打包相关的数据模型，包括：
- 枚举类型：插件来源、任务状态、打包步骤、会话状态
- 请求模型：打包请求、插件项
- 响应模型：打包响应、任务摘要
- 信息模型：任务详情、会话详情

这些模型使用 Pydantic 定义，提供数据验证和序列化功能。
"""

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


class I18nText(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    en_US: str = ""
    zh_Hans: str = ""


class PluginManifest(BaseModel):
    version: str
    author: str
    name: str
    label: I18nText = I18nText()
    description: I18nText = I18nText()
    type: str = "plugin"
    icon: str = ""


class UploadResponse(BaseModel):
    upload_id: str
    author: str
    name: str
    version: str
    label: I18nText
    description: I18nText


class UploadError(BaseModel):
    filename: str
    error: str


class BatchUploadResponse(BaseModel):
    success: list[UploadResponse]
    failed: list[UploadError]


class Architecture(StrEnum):
    LINUX_AMD64 = "linux-amd64"
    LINUX_ARM64 = "linux-arm64"
    DARWIN_AMD64 = "darwin-amd64"
    DARWIN_ARM64 = "darwin-arm64"


class PluginSource(StrEnum):
    """
    插件来源枚举

    定义插件的获取来源：
    - MARKETPLACE: 从 Dify Marketplace 下载
    - LOCAL: 用户上传的本地插件包
    """

    MARKETPLACE = "marketplace"
    LOCAL = "local"


class TaskStatus(StrEnum):
    """
    任务状态枚举

    定义打包任务的生命周期状态：
    - PENDING: 等待处理，任务已入队
    - RUNNING: 正在处理，任务正在执行
    - SUCCESS: 处理成功，打包完成
    - FAILED: 处理失败，打包出错
    - CANCELLED: 已取消，用户主动取消
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PackStep(StrEnum):
    """
    打包步骤枚举

    定义打包流程的各个步骤：
    - DOWNLOADING: 正在从 Marketplace 下载插件包
    - RESOLVING_DEPS: 正在解析插件依赖关系
    - DOWNLOADING_DEPS: 正在下载 Python 依赖包
    - PACKAGING: 正在打包生成离线安装包
    """

    DOWNLOADING = "downloading"
    RESOLVING_DEPS = "resolving_deps"
    DOWNLOADING_DEPS = "downloading_deps"
    PACKAGING = "packaging"


class PackPluginItem(BaseModel):
    """
    打包插件项

    表示一个待打包的插件信息。

    Attributes:
        author: 插件作者标识
        name: 插件名称
        version: 插件版本号
        source: 插件来源，默认为 Marketplace
    """

    author: str
    name: str
    version: str
    source: PluginSource = PluginSource.MARKETPLACE
    architecture: Architecture = Architecture.LINUX_AMD64
    upload_id: str | None = None


class UploadedFileInfo(BaseModel):
    upload_id: str
    file_path: Path
    author: str
    name: str
    version: str
    created_at: datetime
    expires_at: datetime


class PackRequest(BaseModel):
    """
    打包请求模型

    用户提交的打包请求，包含一个或多个待打包的插件。

    Attributes:
        plugins: 待打包的插件列表，不能为空
    """

    plugins: list[PackPluginItem]

    @field_validator("plugins")
    @classmethod
    def plugins_must_not_be_empty(cls, v):
        """
        验证插件列表不能为空

        Args:
            v: 插件列表

        Returns:
            验证通过的插件列表

        Raises:
            ValueError: 插件列表为空时抛出
        """
        if len(v) == 0:
            raise ValueError("plugins list must not be empty")
        return v


class PackTaskSummary(BaseModel):
    """
    打包任务摘要

    返回给客户端的任务摘要信息，用于展示任务状态。

    Attributes:
        task_id: 任务唯一标识
        author: 插件作者
        name: 插件名称
        version: 插件版本
        status: 当前任务状态
    """

    task_id: str
    author: str
    name: str
    version: str
    status: TaskStatus


class PackResponse(BaseModel):
    """
    打包响应模型

    打包请求的响应，包含会话ID和任务摘要列表。

    Attributes:
        session_id: 会话唯一标识，用于订阅 SSE 事件
        tasks: 任务摘要列表
    """

    session_id: str
    tasks: list[PackTaskSummary]


class PackTaskInfo(BaseModel):
    """
    打包任务详情

    存储任务的完整信息，包括状态、进度和结果。

    Attributes:
        task_id: 任务唯一标识
        session_id: 所属会话ID
        author: 插件作者
        name: 插件名称
        version: 插件版本
        source: 插件来源
        local_file_path: 本地插件文件路径（仅本地插件）
        status: 当前任务状态
        current_step: 当前执行步骤
        error_message: 错误消息（失败时）
        raw_error: 原始错误详情（失败时）
        result_file_path: 打包结果文件路径（成功时）
        created_at: 创建时间
        updated_at: 最后更新时间
    """

    task_id: str
    session_id: str
    author: str
    name: str
    version: str
    source: PluginSource
    architecture: Architecture = Architecture.LINUX_AMD64
    upload_id: str | None = None
    local_file_path: Path | None = None
    status: TaskStatus = TaskStatus.PENDING
    current_step: PackStep | None = None
    step_detail: str | None = None
    error_message: str | None = None
    raw_error: str | None = None
    result_file_path: Path | None = None
    created_at: datetime
    updated_at: datetime


class SessionStatus(StrEnum):
    """
    会话状态枚举

    定义打包会话的状态：
    - ACTIVE: 会话活跃，有任务正在处理
    - COMPLETED: 会话完成，所有任务已结束
    """

    ACTIVE = "active"
    COMPLETED = "completed"


class PackSessionInfo(BaseModel):
    """
    打包会话详情

    存储会话的完整信息，一个会话可包含多个打包任务。

    Attributes:
        session_id: 会话唯一标识
        task_ids: 该会话包含的任务ID列表
        status: 会话状态
        created_at: 创建时间
    """

    session_id: str
    task_ids: list[str]
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime
