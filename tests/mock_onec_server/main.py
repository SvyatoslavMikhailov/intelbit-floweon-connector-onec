"""Полный FastAPI-мок 1С HTTPСервисов и OData для контрактных тестов.

Эмулирует два интерфейса:
- /odata/standard.odata/…     — стандартный OData (для OneCODataClient)
- /api/orders/                — кастомный HTTPСервис (для OneCHttpServiceClient)
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request

app = FastAPI(title="1С Mock Server", version="0.0.1")

# ---------------------------------------------------------------------------
# Тестовые данные (in-memory)
# ---------------------------------------------------------------------------

_PRODUCTS: list[dict[str, Any]] = [
    {
        "Ref_Key": "product-guid-0001",
        "Description": "Смартфон Pixel 8",
        "Code": "PX8-001",
        "ЕдиницаИзмерения_Key": "unit-guid-001",
        "ВидНоменклатуры_Key": "cat-guid-001",
    },
    {
        "Ref_Key": "product-guid-0002",
        "Description": "Наушники Sony WH-1000XM5",
        "Code": "SONY-WH-0001",
        "ЕдиницаИзмерения_Key": "unit-guid-001",
        "ВидНоменклатуры_Key": "cat-guid-002",
    },
    {
        "Ref_Key": "product-guid-0003",
        "Description": "Кабель USB-C 2м",
        "Code": "CBL-USBC-2M",
        "ЕдиницаИзмерения_Key": "unit-guid-001",
        "ВидНоменклатуры_Key": "cat-guid-003",
    },
]

_COUNTERPARTIES: list[dict[str, Any]] = [
    {
        "Ref_Key": "cp-guid-0001",
        "Description": "ООО Кибертех",
        "ИНН": "7700000001",
        "КПП": "770001001",
    },
    {
        "Ref_Key": "cp-guid-0002",
        "Description": "ИП Иванов И.И.",
        "ИНН": "770000000001",
        "КПП": "",
    },
]

_STOCKS: list[dict[str, Any]] = [
    {
        "Номенклатура_Key": "product-guid-0001",
        "Склад_Key": "wh-guid-0001",
        "КоличествоОстаток": 42.0,
    },
    {
        "Номенклатура_Key": "product-guid-0002",
        "Склад_Key": "wh-guid-0001",
        "КоличествоОстаток": 17.0,
    },
    {
        "Номенклатура_Key": "product-guid-0003",
        "Склад_Key": "wh-guid-0002",
        "КоличествоОстаток": 0.0,
    },
]

_ORDERS: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# OData: GET /odata/standard.odata/{entity}
# ---------------------------------------------------------------------------


@app.get("/odata/standard.odata/Catalog_Номенклатура")
async def odata_products(
    top: str = Query(default="100", alias="$top"),
    skip: str = Query(default="0", alias="$skip"),
    fmt: str = Query(default="json", alias="$format"),
    filter_: str | None = Query(default=None, alias="$filter"),
) -> dict[str, Any]:
    """OData-выборка номенклатуры (совместимо с OneCODataClient.query)."""
    items = list(_PRODUCTS)
    if filter_:
        # Упрощённая фильтрация: ищем подстроку в Description
        needle = filter_.split("'")[1] if "'" in filter_ else filter_
        items = [p for p in items if needle.lower() in p["Description"].lower()]
    n_skip = int(skip)
    n_top = int(top)
    return {"value": items[n_skip : n_skip + n_top], "@odata.count": len(items)}


@app.get("/odata/standard.odata/Catalog_Контрагент")
async def odata_counterparties(
    top: str = Query(default="100", alias="$top"),
    skip: str = Query(default="0", alias="$skip"),
    fmt: str = Query(default="json", alias="$format"),
    filter_: str | None = Query(default=None, alias="$filter"),
) -> dict[str, Any]:
    """OData-выборка контрагентов."""
    items = list(_COUNTERPARTIES)
    n_skip = int(skip)
    n_top = int(top)
    return {"value": items[n_skip : n_skip + n_top], "@odata.count": len(items)}


@app.get("/odata/standard.odata/Catalog_Склад")
async def odata_warehouses(
    top: str = Query(default="100", alias="$top"),
    skip: str = Query(default="0", alias="$skip"),
    fmt: str = Query(default="json", alias="$format"),
) -> dict[str, Any]:
    """OData-выборка складов."""
    warehouses = [
        {"Ref_Key": "wh-guid-0001", "Description": "Основной склад"},
        {"Ref_Key": "wh-guid-0002", "Description": "Склад брака"},
    ]
    n_skip = int(skip)
    n_top = int(top)
    return {"value": warehouses[n_skip : n_skip + n_top], "@odata.count": len(warehouses)}


@app.get("/odata/standard.odata/AccumulationRegister_ТоварыНаСкладах_Balance")
async def odata_stocks(
    top: str = Query(default="200", alias="$top"),
    skip: str = Query(default="0", alias="$skip"),
    fmt: str = Query(default="json", alias="$format"),
    filter_: str | None = Query(default=None, alias="$filter"),
) -> dict[str, Any]:
    """OData-выборка остатков."""
    items = [s for s in _STOCKS if s["КоличествоОстаток"] > 0]
    n_skip = int(skip)
    n_top = int(top)
    return {"value": items[n_skip : n_skip + n_top], "@odata.count": len(items)}


# ---------------------------------------------------------------------------
# Кастомный HTTP-сервис: /api/orders/
# ---------------------------------------------------------------------------


@app.post("/api/orders/")
async def create_order(request: Request) -> dict[str, Any]:
    """Создание заказа покупателя — аналог POST /intelbit_river/orders/."""
    body: dict[str, Any] = await request.json()

    order_number = body.get("order_number", "")
    if not order_number:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "about:blank",
                "title": "ERR_VALIDATION",
                "status": 400,
                "detail": "Поле order_number обязательно",
            },
        )

    ref_key = str(uuid.uuid4())
    order: dict[str, Any] = {
        "ref_key": ref_key,
        "order_number": order_number,
        "status": "НеСогласован",
        "created_at": "2026-05-28T12:00:00Z",
        "counterparty_ref_key": body.get("counterparty_ref_key", ""),
        "order_ref_key": body.get("order_ref_key", ref_key),
    }
    _ORDERS.append(order)
    return order


@app.get("/api/orders/")
async def get_orders(
    ref_key: str | None = Query(default=None),
    status: str | None = Query(default=None),
    top: int = Query(default=50, alias="$top"),
    skip: int = Query(default=0, alias="$skip"),
) -> dict[str, Any]:
    """Список заказов с опциональной фильтрацией."""
    items = list(_ORDERS)
    if ref_key:
        items = [o for o in items if o["ref_key"] == ref_key]
    if status:
        items = [o for o in items if o["status"] == status]
    return {"value": items[skip : skip + top], "count": len(items)}
