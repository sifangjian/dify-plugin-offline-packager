import pytest
from pydantic import ValidationError

from app.models.marketplace import (
    BatchRequest,
    BatchResponse,
    CollectionInfo,
    CollectionsResponse,
    ErrorDetail,
    ErrorResponse,
    I18nText,
    PluginInfo,
    PluginResource,
    PluginVerification,
    SearchRequest,
    SearchResponse,
)


class TestI18nText:
    def test_default_values(self):
        text = I18nText()
        assert text.en_US == ""
        assert text.zh_Hans == ""

    def test_custom_values(self):
        text = I18nText(en_US="Hello", zh_Hans="你好")
        assert text.en_US == "Hello"
        assert text.zh_Hans == "你好"

    def test_partial_values(self):
        text = I18nText(en_US="Plugin")
        assert text.en_US == "Plugin"
        assert text.zh_Hans == ""


class TestPluginVerification:
    def test_default_values(self):
        v = PluginVerification()
        assert v.authorized_category == ""

    def test_custom_values(self):
        v = PluginVerification(authorized_category="model")
        assert v.authorized_category == "model"


class TestPluginResource:
    def test_default_values(self):
        r = PluginResource()
        assert r.memory == 0

    def test_custom_values(self):
        r = PluginResource(memory=512)
        assert r.memory == 512


class TestPluginInfo:
    def test_valid_minimal_data(self):
        plugin = PluginInfo(
            type="plugin",
            name="agent",
            org="langgenius",
            plugin_id="langgenius/agent",
        )
        assert plugin.type == "plugin"
        assert plugin.name == "agent"
        assert plugin.org == "langgenius"
        assert plugin.plugin_id == "langgenius/agent"

    def test_optional_fields_default_values(self):
        plugin = PluginInfo(
            type="plugin",
            name="agent",
            org="langgenius",
            plugin_id="langgenius/agent",
        )
        assert plugin.icon == ""
        assert plugin.label == I18nText()
        assert plugin.brief == I18nText()
        assert plugin.introduction == ""
        assert plugin.category == ""
        assert plugin.install_count == 0
        assert plugin.latest_version == ""
        assert plugin.tags == []
        assert plugin.verification is None
        assert plugin.badges == []
        assert plugin.repository is None
        assert plugin.resource is None
        assert plugin.privacy_policy == ""

    def test_full_data(self):
        plugin = PluginInfo(
            type="plugin",
            name="agent",
            org="langgenius",
            plugin_id="langgenius/agent",
            icon="https://example.com/icon.png",
            label=I18nText(en_US="Agent", zh_Hans="智能体"),
            brief=I18nText(en_US="An agent plugin", zh_Hans="智能体插件"),
            introduction="This is an agent plugin",
            category="agent",
            created_at="2024-01-01",
            updated_at="2024-06-01",
            install_count=1000,
            latest_version="0.0.1",
            latest_package_identifier="abc123",
            status="active",
            tags=["agent", "tool"],
            verification=PluginVerification(authorized_category="agent"),
            badges=[{"id": "verified", "label": "Verified"}],
            repository="https://github.com/langgenius/agent",
            resource=PluginResource(memory=512),
            privacy_policy="https://example.com/privacy",
        )
        assert plugin.icon == "https://example.com/icon.png"
        assert plugin.label.en_US == "Agent"
        assert plugin.brief.zh_Hans == "智能体插件"
        assert plugin.install_count == 1000
        assert plugin.verification.authorized_category == "agent"
        assert plugin.resource.memory == 512
        assert len(plugin.tags) == 2

    def test_missing_required_field_type(self):
        with pytest.raises(ValidationError) as exc_info:
            PluginInfo(
                name="agent",
                org="langgenius",
                plugin_id="langgenius/agent",
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "type" in field_names

    def test_missing_required_field_name(self):
        with pytest.raises(ValidationError) as exc_info:
            PluginInfo(
                type="plugin",
                org="langgenius",
                plugin_id="langgenius/agent",
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "name" in field_names

    def test_missing_required_field_org(self):
        with pytest.raises(ValidationError) as exc_info:
            PluginInfo(
                type="plugin",
                name="agent",
                plugin_id="langgenius/agent",
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "org" in field_names

    def test_missing_required_field_plugin_id(self):
        with pytest.raises(ValidationError) as exc_info:
            PluginInfo(
                type="plugin",
                name="agent",
                org="langgenius",
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "plugin_id" in field_names

    def test_missing_all_required_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            PluginInfo()
        errors = exc_info.value.errors()
        assert len(errors) == 4
        field_names = {e["loc"][0] for e in errors}
        assert field_names == {"type", "name", "org", "plugin_id"}

    def test_from_dict_with_valid_json(self):
        data = {
            "type": "plugin",
            "name": "agent",
            "org": "langgenius",
            "plugin_id": "langgenius/agent",
            "label": {"en_US": "Agent", "zh_Hans": "智能体"},
            "install_count": 500,
        }
        plugin = PluginInfo(**data)
        assert plugin.label.en_US == "Agent"
        assert plugin.install_count == 500


class TestSearchRequest:
    def test_default_values(self):
        req = SearchRequest()
        assert req.keyword == ""
        assert req.category == ""
        assert req.page == 1
        assert req.page_size == 20

    def test_custom_values(self):
        req = SearchRequest(keyword="agent", category="model", page=2, page_size=10)
        assert req.keyword == "agent"
        assert req.category == "model"
        assert req.page == 2
        assert req.page_size == 10

    def test_partial_values(self):
        req = SearchRequest(keyword="test")
        assert req.keyword == "test"
        assert req.category == ""
        assert req.page == 1
        assert req.page_size == 20


class TestSearchResponse:
    def test_with_plugins(self):
        plugins = [
            PluginInfo(
                type="plugin",
                name="agent",
                org="langgenius",
                plugin_id="langgenius/agent",
            )
        ]
        resp = SearchResponse(plugins=plugins, total=1)
        assert len(resp.plugins) == 1
        assert resp.total == 1
        assert resp.plugins[0].name == "agent"

    def test_empty_response(self):
        resp = SearchResponse(plugins=[], total=0)
        assert resp.plugins == []
        assert resp.total == 0


class TestCollectionInfo:
    def test_required_and_default_fields(self):
        col = CollectionInfo(
            name="featured",
            label=I18nText(en_US="Featured", zh_Hans="精选"),
            description=I18nText(en_US="Featured plugins", zh_Hans="精选插件"),
        )
        assert col.name == "featured"
        assert col.label.en_US == "Featured"
        assert col.description.zh_Hans == "精选插件"
        assert col.searchable is False
        assert col.search_params == {}
        assert col.priority == 0

    def test_full_data(self):
        col = CollectionInfo(
            name="featured",
            label=I18nText(en_US="Featured", zh_Hans="精选"),
            description=I18nText(en_US="Featured plugins", zh_Hans="精选插件"),
            searchable=True,
            search_params={"sort_by": "install_count"},
            priority=10,
        )
        assert col.searchable is True
        assert col.search_params == {"sort_by": "install_count"}
        assert col.priority == 10

    def test_missing_required_field_name(self):
        with pytest.raises(ValidationError) as exc_info:
            CollectionInfo(
                label=I18nText(),
                description=I18nText(),
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "name" in field_names


class TestCollectionsResponse:
    def test_with_collections(self):
        collections = [
            CollectionInfo(
                name="featured",
                label=I18nText(en_US="Featured"),
                description=I18nText(en_US="Featured plugins"),
            )
        ]
        resp = CollectionsResponse(collections=collections, total=1)
        assert len(resp.collections) == 1
        assert resp.total == 1
        assert resp.collections[0].name == "featured"

    def test_empty_response(self):
        resp = CollectionsResponse(collections=[], total=0)
        assert resp.collections == []
        assert resp.total == 0


class TestBatchRequest:
    def test_with_plugin_ids(self):
        req = BatchRequest(plugin_ids=["langgenius/agent", "langgenius/chat"])
        assert len(req.plugin_ids) == 2
        assert req.plugin_ids[0] == "langgenius/agent"

    def test_empty_plugin_ids(self):
        req = BatchRequest(plugin_ids=[])
        assert req.plugin_ids == []

    def test_missing_plugin_ids(self):
        with pytest.raises(ValidationError) as exc_info:
            BatchRequest()
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "plugin_ids" in field_names


class TestBatchResponse:
    def test_with_plugins(self):
        plugins = [
            PluginInfo(
                type="plugin",
                name="agent",
                org="langgenius",
                plugin_id="langgenius/agent",
            ),
            PluginInfo(
                type="plugin",
                name="chat",
                org="langgenius",
                plugin_id="langgenius/chat",
            ),
        ]
        resp = BatchResponse(plugins=plugins)
        assert len(resp.plugins) == 2

    def test_empty_response(self):
        resp = BatchResponse(plugins=[])
        assert resp.plugins == []


class TestErrorDetail:
    def test_fields(self):
        detail = ErrorDetail(code="NOT_FOUND", message="未找到该插件")
        assert detail.code == "NOT_FOUND"
        assert detail.message == "未找到该插件"


class TestErrorResponse:
    def test_structure(self):
        error = ErrorResponse(error=ErrorDetail(code="INTERNAL_ERROR", message="服务内部错误"))
        assert error.error.code == "INTERNAL_ERROR"
        assert error.error.message == "服务内部错误"

    def test_serialization(self):
        error = ErrorResponse(error=ErrorDetail(code="NOT_FOUND", message="未找到该插件"))
        data = error.model_dump()
        assert data == {"error": {"code": "NOT_FOUND", "message": "未找到该插件"}}
