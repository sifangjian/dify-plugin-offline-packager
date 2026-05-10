from pydantic import BaseModel


class I18nText(BaseModel):
    en_US: str = ""
    zh_Hans: str = ""


class PluginVerification(BaseModel):
    authorized_category: str = ""


class PluginResource(BaseModel):
    memory: int = 0


class PluginInfo(BaseModel):
    type: str
    name: str
    org: str
    plugin_id: str
    icon: str = ""
    label: I18nText = I18nText()
    brief: I18nText = I18nText()
    introduction: str = ""
    category: str = ""
    created_at: str = ""
    updated_at: str = ""
    install_count: int = 0
    latest_version: str = ""
    latest_package_identifier: str = ""
    status: str = ""
    tags: list[str] = []
    verification: PluginVerification | None = None
    badges: list[dict] = []
    repository: str | None = None
    resource: PluginResource | None = None
    privacy_policy: str = ""


class SearchRequest(BaseModel):
    keyword: str = ""
    category: str = ""
    page: int = 1
    page_size: int = 20


class SearchResponse(BaseModel):
    plugins: list[PluginInfo]
    total: int


class CollectionInfo(BaseModel):
    name: str
    label: I18nText
    description: I18nText
    searchable: bool = False
    search_params: dict = {}
    priority: int = 0


class CollectionsResponse(BaseModel):
    collections: list[CollectionInfo]
    total: int


class BatchRequest(BaseModel):
    plugin_ids: list[str]


class BatchResponse(BaseModel):
    plugins: list[PluginInfo]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
