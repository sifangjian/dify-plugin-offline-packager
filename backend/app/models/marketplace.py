"""
Marketplace 数据模型模块

定义与 Dify Marketplace API 交互相关的数据模型，包括：
- 插件信息模型：PluginInfo 及其嵌套模型
- 搜索相关模型：SearchRequest、SearchResponse
- 集合相关模型：CollectionInfo、CollectionsResponse
- 批量查询模型：BatchRequest、BatchResponse
- 错误响应模型：ErrorResponse

这些模型与 Marketplace API 的响应格式保持一致。
"""

from pydantic import BaseModel


class I18nText(BaseModel):
    """
    国际化文本

    支持多语言的文本内容。

    Attributes:
        en_US: 英文文本
        zh_Hans: 简体中文文本
    """

    en_US: str = ""
    zh_Hans: str = ""


class PluginVerification(BaseModel):
    """
    插件验证信息

    插件的官方验证状态。

    Attributes:
        authorized_category: 授权分类
    """

    authorized_category: str = ""


class PluginResource(BaseModel):
    """
    插件资源需求

    插件运行所需的系统资源。

    Attributes:
        memory: 内存需求（MB）
    """

    memory: int = 0


class ReadmeMeta(BaseModel):
    """
    README 元信息

    插件介绍文档的多语言可用性信息。

    Attributes:
        available_languages: 可用的语言版本列表
    """

    available_languages: list[str] = []


class PluginTag(BaseModel):
    """
    插件标签

    用于分类和搜索的标签。

    Attributes:
        name: 标签名称
    """

    name: str = ""


class PluginInfo(BaseModel):
    """
    插件详细信息

    从 Marketplace 获取的插件完整信息。

    Attributes:
        type: 插件类型
        name: 插件名称
        org: 所属组织
        plugin_id: 插件唯一标识
        label: 显示名称（国际化）
        brief: 简短描述（国际化）
        introduction: 详细介绍
        category: 分类
        created_at: 创建时间
        updated_at: 更新时间
        install_count: 安装次数
        latest_version: 最新版本号
        latest_package_identifier: 最新包标识符
        status: 插件状态
        tags: 标签列表
        verification: 验证信息
        badges: 徽章列表
        repository: 代码仓库地址
        resource: 资源需求
        privacy_policy: 隐私政策链接
    """

    type: str
    name: str
    org: str
    plugin_id: str
    label: I18nText = I18nText()
    brief: I18nText = I18nText()
    introduction: str = ""
    readme_meta: ReadmeMeta = ReadmeMeta()
    category: str = ""
    created_at: str = ""
    updated_at: str = ""
    install_count: int = 0
    latest_version: str = ""
    latest_package_identifier: str = ""
    status: str = ""
    tags: list[PluginTag] = []
    verification: PluginVerification | None = None
    badges: list[dict | str] = []
    repository: str | None = None
    resource: PluginResource | None = None
    privacy_policy: str = ""


class SearchRequest(BaseModel):
    """
    搜索请求模型

    插件搜索的请求参数。

    Attributes:
        keyword: 搜索关键词
        category: 分类筛选
        page: 页码
        page_size: 每页数量
    """

    keyword: str = ""
    category: str = ""
    page: int = 1
    page_size: int = 20


class SearchResponse(BaseModel):
    """
    搜索响应模型

    插件搜索的结果。

    Attributes:
        plugins: 插件列表
        total: 总数量
    """

    plugins: list[PluginInfo]
    total: int


class CollectionInfo(BaseModel):
    """
    插件集合信息

    Marketplace 中的插件集合（专题）。

    Attributes:
        name: 集合名称
        label: 显示名称（国际化）
        description: 描述（国际化）
        searchable: 是否可搜索
        search_params: 搜索参数
        priority: 显示优先级
    """

    name: str
    label: I18nText
    description: I18nText
    searchable: bool = False
    search_params: dict = {}
    priority: int = 0


class CollectionsResponse(BaseModel):
    """
    集合列表响应

    获取插件集合列表的结果。

    Attributes:
        collections: 集合列表
        total: 总数量
    """

    collections: list[CollectionInfo]
    total: int


class BatchRequest(BaseModel):
    """
    批量查询请求

    批量获取插件信息的请求参数。

    Attributes:
        plugin_ids: 插件ID列表
    """

    plugin_ids: list[str]


class BatchResponse(BaseModel):
    """
    批量查询响应

    批量获取插件信息的结果。

    Attributes:
        plugins: 插件列表
    """

    plugins: list[PluginInfo]


class ErrorDetail(BaseModel):
    """
    错误详情

    API 错误响应的详细信息。

    Attributes:
        code: 错误代码
        message: 错误消息
    """

    code: str
    message: str


class ErrorResponse(BaseModel):
    """
    错误响应模型

    API 错误响应的标准格式。

    Attributes:
        error: 错误详情
    """

    error: ErrorDetail
