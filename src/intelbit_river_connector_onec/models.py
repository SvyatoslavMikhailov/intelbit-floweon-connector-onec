"""Pydantic-модели 1С-сущностей для коннектора."""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class NomenclatureType(StrEnum):
    product = "product"
    service = "service"
    work = "work"


class NomenclatureItem(BaseModel):
    """Номенклатура 1С."""

    guid: str
    code: str
    name: str
    full_name: str = ""
    type: NomenclatureType = NomenclatureType.product
    unit: str = "шт"
    vat_rate: str = "VAT20"
    is_archived: bool = False


class Warehouse(BaseModel):
    """Склад 1С."""

    guid: str
    code: str
    name: str
    is_main: bool = False


class Counterparty(BaseModel):
    """Контрагент 1С."""

    guid: str
    code: str
    name: str
    inn: str = ""
    kpp: str = ""
    is_customer: bool = True
    is_supplier: bool = False


class OrderStatus(StrEnum):
    draft = "draft"
    confirmed = "confirmed"
    shipped = "shipped"
    closed = "closed"
    cancelled = "cancelled"


class OrderLine(BaseModel):
    """Строка заказа покупателя."""

    line_number: int
    nomenclature_guid: str
    quantity: Decimal
    price: Decimal
    amount: Decimal
    vat_amount: Decimal = Decimal("0")


class SalesOrder(BaseModel):
    """Заказ покупателя 1С."""

    guid: str
    number: str
    date: str
    status: OrderStatus = OrderStatus.draft
    counterparty_guid: str
    warehouse_guid: str = ""
    lines: list[OrderLine] = Field(default_factory=list)
    comment: str = ""
