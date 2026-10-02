"""Тесты OneCODataClient: $filter / $top / $skip / $expand / get by key."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from intelbit_floweon_connector_onec.auth import BasicAuth
from intelbit_floweon_connector_onec.odata import OneCODataClient

FIXTURES = Path(__file__).parent / "fixtures" / "onec-mocks" / "odata"


def _make_client() -> OneCODataClient:
    auth = BasicAuth("admin", "pass")
    config = {"base_url": "https://1c.example.com/odata/standard.odata"}
    return OneCODataClient(config, auth)


class TestOneCODataClient:
    @pytest.mark.asyncio
    async def test_query_returns_value_list(self, httpx_mock: HTTPXMock) -> None:
        import json as _json

        data = _json.loads((FIXTURES / "Номенклатура_response.json").read_bytes())
        httpx_mock.add_response(json=data)
        client = _make_client()
        result = await client.query("Catalog_Номенклатура")
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["Code"] == "00001"

    @pytest.mark.asyncio
    async def test_query_with_filter_param(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"value": []})
        client = _make_client()
        await client.query("Catalog_Номенклатура", filter="DeletionMark eq false")
        request = httpx_mock.get_requests()[0]
        url_str = str(request.url)
        assert "%24filter" in url_str or "$filter" in url_str
        assert "DeletionMark" in url_str

    @pytest.mark.asyncio
    async def test_query_top_skip_params(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"value": []})
        client = _make_client()
        await client.query("Catalog_Номенклатура", top=10, skip=20)
        request = httpx_mock.get_requests()[0]
        url_str = str(request.url)
        assert "%24top=10" in url_str or "$top=10" in url_str
        assert "%24skip=20" in url_str or "$skip=20" in url_str

    @pytest.mark.asyncio
    async def test_query_expand_param(self, httpx_mock: HTTPXMock) -> None:
        expanded = [{"Ref_Key": "x", "Производитель": {"Name": "Dell"}}]
        httpx_mock.add_response(json={"value": expanded})
        client = _make_client()
        result = await client.query("Catalog_Номенклатура", expand="Производитель")
        request = httpx_mock.get_requests()[0]
        assert "%24expand" in str(request.url) or "$expand" in str(request.url)
        assert result[0]["Производитель"]["Name"] == "Dell"

    @pytest.mark.asyncio
    async def test_query_empty_result(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"value": []})
        client = _make_client()
        result = await client.query("Catalog_Номенклатура", filter="Code eq '99999'")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_key_found(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json={
                "Ref_Key": "nom-guid-0001",
                "Code": "00001",
                "Description": "Ноутбук Dell XPS 13",
            }
        )
        client = _make_client()
        result = await client.get("Catalog_Номенклатура", "nom-guid-0001")
        assert result is not None
        assert result["Code"] == "00001"

    @pytest.mark.asyncio
    async def test_get_by_key_not_found_returns_none(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")
        client = _make_client()
        result = await client.get("Catalog_Номенклатура", "nonexistent-guid")
        assert result is None
