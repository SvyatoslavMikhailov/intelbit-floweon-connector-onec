"""Fail-closed конфигурации коннектора 1С (4-17-23, часть D) и C-6 аудита."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from intelbit_floweon_connector_onec import ConfigurationError
from intelbit_floweon_connector_onec.auth import BasicAuth
from intelbit_floweon_connector_onec.connector import OneCConnector, _build_odata_filter
from intelbit_floweon_connector_onec.enterprise_data import EnterpriseDataClient
from intelbit_floweon_connector_onec.webhooks import OneCWebhookReceiver, WebhookSignatureError

SECRET = "test-webhook-secret-32-bytes-long"


@pytest.fixture
def full_config() -> dict[str, Any]:
    """Полный валидный конфиг с явным тестовым секретом вебхуков."""
    return {
        "auth": {"type": "basic", "username": "admin", "password": "pass"},
        "enterprise_data": {"base_url": "https://1c.example.com"},
        "http_service": {"base_url": "https://1c.example.com"},
        "odata": {"base_url": "https://1c.example.com/odata/standard.odata"},
        "webhooks": {"webhook_secret": SECRET},
    }


class TestWebhookSecretFailClosed:
    def test_full_config_ok(self, full_config: dict[str, Any]) -> None:
        OneCConnector(full_config)

    def test_missing_secret_raises(self, full_config: dict[str, Any]) -> None:
        full_config["webhooks"] = {}
        with pytest.raises(ConfigurationError, match="webhook_secret"):
            OneCConnector(full_config)

    def test_missing_webhooks_section_raises(self, full_config: dict[str, Any]) -> None:
        del full_config["webhooks"]
        with pytest.raises(ConfigurationError):
            OneCConnector(full_config)

    def test_empty_secret_raises(self, full_config: dict[str, Any]) -> None:
        full_config["webhooks"] = {"webhook_secret": "   "}
        with pytest.raises(ConfigurationError):
            OneCConnector(full_config)

    def test_short_secret_raises_without_value(self, full_config: dict[str, Any]) -> None:
        short = "short-s3cr3t"
        full_config["webhooks"] = {"webhook_secret": short}
        with pytest.raises(ConfigurationError) as exc_info:
            OneCConnector(full_config)
        assert short not in str(exc_info.value)

    def test_no_dev_secret_default(self, full_config: dict[str, Any]) -> None:
        """Старый дефолт "dev-secret" больше не подставляется."""
        del full_config["webhooks"]
        with pytest.raises(ConfigurationError):
            OneCConnector(full_config)

    def test_receiver_requires_secret(self) -> None:
        with pytest.raises(ConfigurationError):
            OneCWebhookReceiver({})

    def test_disabled_webhooks_without_secret_ok(self, full_config: dict[str, Any]) -> None:
        full_config["webhooks"] = {"enabled": False}
        OneCConnector(full_config)

    async def test_disabled_webhooks_rejects_requests(self, full_config: dict[str, Any]) -> None:
        full_config["webhooks"] = {"enabled": False}
        connector = OneCConnector(full_config)
        with pytest.raises(WebhookSignatureError):
            await connector.on_webhook({}, b"{}")


class TestBaseUrlRequired:
    @pytest.mark.parametrize("section", ["enterprise_data", "http_service", "odata"])
    def test_missing_section_raises(self, full_config: dict[str, Any], section: str) -> None:
        cfg = copy.deepcopy(full_config)
        del cfg[section]
        with pytest.raises(ConfigurationError, match=f"{section}.base_url"):
            OneCConnector(cfg)

    @pytest.mark.parametrize("section", ["enterprise_data", "http_service", "odata"])
    def test_empty_base_url_raises(self, full_config: dict[str, Any], section: str) -> None:
        cfg = copy.deepcopy(full_config)
        cfg[section] = {"base_url": ""}
        with pytest.raises(ConfigurationError):
            OneCConnector(cfg)


class TestODataFilterEscaping:
    def test_quote_is_doubled(self) -> None:
        assert _build_odata_filter({"Description": "O'Reilly"}) == "Description eq 'O''Reilly'"

    def test_injection_value_stays_literal(self) -> None:
        result = _build_odata_filter({"Code": "1' or 1 eq 1 or 'a"})
        assert result == "Code eq '1'' or 1 eq 1 or ''a'"

    def test_cyrillic_key_allowed(self) -> None:
        assert _build_odata_filter({"Артикул": "A-1"}) == "Артикул eq 'A-1'"

    @pytest.mark.parametrize(
        "bad_key", ["Code eq '1' or Code", "1Code", "Code)", "", "Ref Key", "a/b", "x'"]
    )
    def test_bad_key_raises(self, bad_key: str) -> None:
        with pytest.raises(ValueError):
            _build_odata_filter({bad_key: "v"})

    async def test_connector_sends_escaped_filter(
        self, full_config: dict[str, Any], httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(json={"value": []})
        connector = OneCConnector(full_config)
        await connector.read_catalog("Номенклатура", filter={"Description": "O'Reilly"})
        request = httpx_mock.get_requests()[0]
        assert request.url.params["$filter"] == "Description eq 'O''Reilly'"


class TestEnterpriseDataXxe:
    def test_entities_not_resolved(self, tmp_path: Path) -> None:
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("TOP-SECRET-CONTENT")
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Message [
  <!ENTITY ext SYSTEM "file://{secret_file}">
  <!ENTITY internal "EXPANDED-INTERNAL">
]>
<Message xmlns="urn:1C.ru:EnterpriseData:1.5">
  <Body>
    <Custom><Field>&ext;</Field><Other>&internal;</Other></Custom>
  </Body>
</Message>""".encode()
        client = EnterpriseDataClient(
            {"base_url": "https://1c.example.com"}, BasicAuth(username="u", password="p")
        )
        messages = client._parse_xml(xml)
        dumped = repr(messages)
        assert "TOP-SECRET-CONTENT" not in dumped
        assert "EXPANDED-INTERNAL" not in dumped
