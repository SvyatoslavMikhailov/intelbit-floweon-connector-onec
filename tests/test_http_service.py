"""Тесты OneCHttpServiceClient: retry, idempotency, обработка ошибок 1С."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from intelbit_river_connector_onec.auth import BasicAuth
from intelbit_river_connector_onec.http_service import OneCHttpServiceClient, OneCHttpServiceError


def _make_client() -> OneCHttpServiceClient:
    auth = BasicAuth("admin", "pass")
    config = {"base_url": "https://1c.example.com", "timeout": 5.0}
    return OneCHttpServiceClient(config, auth)


class TestOneCHttpServiceClient:
    @pytest.mark.asyncio
    async def test_successful_post(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://1c.example.com/api/orders/",
            json={"Ref_Key": "order-001", "Number": "Ш000001"},
        )
        client = _make_client()
        result = await client.call("POST", "/api/orders/", {"Number": "Ш000001"})
        assert result["Ref_Key"] == "order-001"

    @pytest.mark.asyncio
    async def test_post_includes_idempotency_key(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url="https://1c.example.com/api/orders/", json={})
        client = _make_client()
        await client.call("POST", "/api/orders/", {})
        request = httpx_mock.get_requests()[0]
        assert "Idempotency-Key" in request.headers

    @pytest.mark.asyncio
    async def test_get_no_idempotency_key(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url="https://1c.example.com/api/catalog/", json={"value": []})
        client = _make_client()
        await client.call("GET", "/api/catalog/")
        request = httpx_mock.get_requests()[0]
        assert "Idempotency-Key" not in request.headers

    @pytest.mark.asyncio
    async def test_correct_headers_sent(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url="https://1c.example.com/api/test/", json={})
        client = _make_client()
        await client.call("GET", "/api/test/")
        request = httpx_mock.get_requests()[0]
        assert request.headers["Accept"] == "application/json"
        assert "intelbit-river-connector-onec/0.2.0" in request.headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_400_raises_onec_http_service_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://1c.example.com/api/orders/",
            status_code=400,
            json={"error": {"code": "ERR_VALIDATION", "message": "Не заполнен контрагент"}},
        )
        client = _make_client()
        with pytest.raises(OneCHttpServiceError) as exc_info:
            await client.call("POST", "/api/orders/", {})
        err = exc_info.value
        assert err.status_code == 400
        assert err.error_code == "ERR_VALIDATION"
        assert "контрагент" in err.onec_message

    @pytest.mark.asyncio
    async def test_500_retries_and_eventually_raises(self, httpx_mock: HTTPXMock) -> None:
        # Добавляем 5 ответов 500 — retry исчерпает попытки
        for _ in range(5):
            httpx_mock.add_response(
                url="https://1c.example.com/api/orders/",
                status_code=500,
                json={"error": {"code": "INTERNAL", "message": "Internal server error"}},
            )
        client = _make_client()
        with pytest.raises(OneCHttpServiceError) as exc_info:
            await client.call("POST", "/api/orders/", {})
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_500_then_200_succeeds(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://1c.example.com/api/orders/",
            status_code=500,
            json={"error": {"code": "INTERNAL", "message": "err"}},
        )
        httpx_mock.add_response(
            url="https://1c.example.com/api/orders/",
            status_code=200,
            json={"Ref_Key": "order-ok"},
        )
        client = _make_client()
        result = await client.call("POST", "/api/orders/", {})
        assert result["Ref_Key"] == "order-ok"

    @pytest.mark.asyncio
    async def test_404_raises_with_non_json_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://1c.example.com/api/items/999/",
            status_code=404,
            text="Not Found",
        )
        client = _make_client()
        with pytest.raises(OneCHttpServiceError) as exc_info:
            await client.call("GET", "/api/items/999/")
        assert exc_info.value.status_code == 404
