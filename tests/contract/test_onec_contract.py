"""Контрактные тесты: Python-коннектор ↔ FastAPI-мок 1С сервера.

Проверяют, что shape ответов от mock-сервера совпадает с ожиданиями
OneCODataClient и OneCHttpServiceClient.

Запуск: uv run pytest -m contract -v
"""

import httpx
import pytest

from intelbit_floweon_connector_onec.auth import BasicAuth
from intelbit_floweon_connector_onec.http_service import OneCHttpServiceClient
from intelbit_floweon_connector_onec.odata import OneCODataClient
from tests.mock_onec_server.main import app

pytestmark = pytest.mark.contract

_TRANSPORT = httpx.ASGITransport(app=app)
_BASE_ODATA = "http://test/odata/standard.odata"
_BASE_HTTP = "http://test"
_AUTH = BasicAuth(username="test", password="secret")


# ---------------------------------------------------------------------------
# Тест 1 — каталог номенклатуры через OData
# ---------------------------------------------------------------------------


async def test_odata_catalog_products_contract() -> None:
    """OData /Catalog_Номенклатура возвращает список с обязательными полями."""
    client = OneCODataClient(
        {"base_url": _BASE_ODATA},
        _AUTH,
        _transport=_TRANSPORT,
    )
    items = await client.query("Catalog_Номенклатура", top=10)

    assert isinstance(items, list)
    assert len(items) > 0, "Мок должен вернуть хотя бы одну позицию"

    product = items[0]
    assert "Ref_Key" in product, "OData ответ должен содержать Ref_Key"
    assert "Description" in product, "OData ответ должен содержать Description"


# ---------------------------------------------------------------------------
# Тест 2 — каталог контрагентов через OData
# ---------------------------------------------------------------------------


async def test_odata_catalog_counterparties_contract() -> None:
    """OData /Catalog_Контрагент возвращает список с ИНН."""
    client = OneCODataClient(
        {"base_url": _BASE_ODATA},
        _AUTH,
        _transport=_TRANSPORT,
    )
    items = await client.query("Catalog_Контрагент", top=10)

    assert isinstance(items, list)
    assert len(items) > 0

    cp = items[0]
    assert "Ref_Key" in cp
    assert "Description" in cp
    assert "ИНН" in cp, "Контрагент должен содержать поле ИНН"


# ---------------------------------------------------------------------------
# Тест 3 — создание заказа через HTTPСервис
# ---------------------------------------------------------------------------


async def test_http_service_create_order_contract() -> None:
    """POST /api/orders/ возвращает заказ с ref_key и статусом НеСогласован."""
    client = OneCHttpServiceClient(
        {"base_url": _BASE_HTTP},
        _AUTH,
        _transport=_TRANSPORT,
    )
    result = await client.call(
        "POST",
        "/api/orders/",
        {
            "order_number": "ТЕСТ-CONTRACT-001",
            "order_ref_key": "test-ref-0001",
        },
    )

    assert "ref_key" in result, "Ответ должен содержать ref_key созданного заказа"
    assert result["order_number"] == "ТЕСТ-CONTRACT-001"
    assert result["status"] == "НеСогласован"


# ---------------------------------------------------------------------------
# Тест 4 — получение списка заказов
# ---------------------------------------------------------------------------


async def test_http_service_get_orders_contract() -> None:
    """GET /api/orders/ возвращает список заказов в поле value."""
    # Сначала создаём заказ, чтобы список не был пустым
    writer = OneCHttpServiceClient(
        {"base_url": _BASE_HTTP},
        _AUTH,
        _transport=_TRANSPORT,
    )
    created = await writer.call("POST", "/api/orders/", {"order_number": "ТЕСТ-CONTRACT-LIST"})

    reader = OneCHttpServiceClient(
        {"base_url": _BASE_HTTP},
        _AUTH,
        _transport=_TRANSPORT,
    )
    result = await reader.call("GET", "/api/orders/")

    assert "value" in result, "Ответ GET /api/orders/ должен содержать поле value"
    assert isinstance(result["value"], list)
    assert any(o["ref_key"] == created["ref_key"] for o in result["value"])


# ---------------------------------------------------------------------------
# Тест 5 — остатки через OData
# ---------------------------------------------------------------------------


async def test_odata_stocks_contract() -> None:
    """OData /AccumulationRegister_ТоварыНаСкладах_Balance возвращает остатки."""
    client = OneCODataClient(
        {"base_url": _BASE_ODATA},
        _AUTH,
        _transport=_TRANSPORT,
    )
    items = await client.query("AccumulationRegister_ТоварыНаСкладах_Balance", top=50)

    assert isinstance(items, list)
    assert len(items) > 0, "Мок должен вернуть хотя бы один ненулевой остаток"

    stock = items[0]
    assert "Номенклатура_Key" in stock, "Остаток должен содержать ключ номенклатуры"
    assert "КоличествоОстаток" in stock
    assert stock["КоличествоОстаток"] > 0, "Нулевые остатки не должны попасть в выборку"
