"""Тесты OneCConnector: end-to-end через моки клиентов."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest
from pytest_httpx import HTTPXMock

from intelbit_river_connector_onec.connector import OneCConnector
from intelbit_river_connector_onec.models import OrderLine, SalesOrder
from intelbit_river_connector_onec.webhooks import WebhookSignatureError

SECRET = "test-webhook-secret-32-bytes-long"

_CONFIG = {
    "auth": {"type": "basic", "username": "admin", "password": "pass"},
    "enterprise_data": {
        "base_url": "https://1c.example.com",
        "plan": "ОсновнойПланОбмена",
        "node": "ЦентральныйУзел",
    },
    "http_service": {"base_url": "https://1c.example.com"},
    "odata": {"base_url": "https://1c.example.com/odata/standard.odata"},
    "webhooks": {"webhook_secret": SECRET, "replay_window_sec": 300},
}

_NOMENCLATURE_ODATA = {
    "value": [
        {"Ref_Key": "nom-001", "Code": "00001", "Description": "Ноутбук"},
        {"Ref_Key": "nom-002", "Code": "00002", "Description": "Мышь"},
    ]
}


def _make_sig(body: bytes) -> str:
    t = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


class TestConnectorReadCatalog:
    @pytest.mark.asyncio
    async def test_read_nomenclature_via_odata(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_NOMENCLATURE_ODATA)
        connector = OneCConnector(_CONFIG)
        result = await connector.read_catalog("Номенклатура")
        assert len(result) == 2
        assert result[0]["Code"] == "00001"

    @pytest.mark.asyncio
    async def test_read_counterparty_via_odata(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json={"value": [{"Ref_Key": "cp-001", "Description": "ООО Тест"}]}
        )
        connector = OneCConnector(_CONFIG)
        result = await connector.read_catalog("Контрагент")
        assert result[0]["Description"] == "ООО Тест"

    @pytest.mark.asyncio
    async def test_read_catalog_with_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"value": []})
        connector = OneCConnector(_CONFIG)
        await connector.read_catalog("Номенклатура", filter={"Code": "00001"})
        request = httpx_mock.get_requests()[0]
        assert "Code" in str(request.url)


class TestConnectorCreateOrder:
    @pytest.mark.asyncio
    async def test_create_order_calls_http_service(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json={"Ref_Key": "order-new-001", "Number": "Ш000001"}
        )
        connector = OneCConnector(_CONFIG)
        order = SalesOrder(
            guid="order-local-001",
            number="Ш000001",
            date="2026-05-28",
            counterparty_guid="cp-guid-0001",
            lines=[
                OrderLine(
                    line_number=1,
                    nomenclature_guid="nom-guid-0001",
                    quantity=Decimal("1"),
                    price=Decimal("89990"),
                    amount=Decimal("89990"),
                )
            ],
        )
        result = await connector.create_order(order)
        assert result["Ref_Key"] == "order-new-001"

    @pytest.mark.asyncio
    async def test_create_order_uses_post(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"Ref_Key": "x"})
        connector = OneCConnector(_CONFIG)
        order = SalesOrder(
            guid="o",
            number="1",
            date="2026-05-28",
            counterparty_guid="cp",
        )
        await connector.create_order(order)
        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"


class TestConnectorUpdateBatch:
    @pytest.mark.asyncio
    async def test_update_stocks_returns_message_id(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=200)
        connector = OneCConnector(_CONFIG)
        result = await connector.update_stocks(
            [{"nomenclature_key": "nom-001", "warehouse_key": "wh-001", "quantity": 10}]
        )
        assert "message_id" in result
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_update_prices_returns_message_id(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=200)
        connector = OneCConnector(_CONFIG)
        result = await connector.update_prices(
            [{"nomenclature_key": "nom-001", "price": "89990.00"}]
        )
        assert "message_id" in result
        assert result["count"] == 1


class TestConnectorOnWebhook:
    @pytest.mark.asyncio
    async def test_on_webhook_valid_signature(self) -> None:
        body = json.dumps(
            {"event_type": "catalog.updated", "event_id": "evt-001", "data": {}}
        ).encode()
        sig = _make_sig(body)
        connector = OneCConnector(_CONFIG)
        event = await connector.on_webhook({"X-Signature": sig}, body)
        assert event["event_type"] == "catalog.updated"

    @pytest.mark.asyncio
    async def test_on_webhook_invalid_signature_raises(self) -> None:
        body = b'{"event_type": "catalog.updated", "event_id": "x"}'
        connector = OneCConnector(_CONFIG)
        with pytest.raises(WebhookSignatureError):
            await connector.on_webhook({"X-Signature": "t=123,v1=badhash"}, body)

    @pytest.mark.asyncio
    async def test_config_stored(self) -> None:
        connector = OneCConnector(_CONFIG)
        assert connector.config["auth"]["username"] == "admin"
