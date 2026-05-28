"""Тесты Pydantic-моделей 1С-сущностей."""

from decimal import Decimal

from intelbit_river_connector_onec.models import (
    Counterparty,
    NomenclatureItem,
    NomenclatureType,
    OrderLine,
    OrderStatus,
    SalesOrder,
    Warehouse,
)


class TestNomenclatureItem:
    def test_defaults(self) -> None:
        item = NomenclatureItem(guid="guid-1", code="00001", name="Товар А")
        assert item.type == NomenclatureType.product
        assert item.unit == "шт"
        assert not item.is_archived

    def test_service_type(self) -> None:
        item = NomenclatureItem(
            guid="guid-2", code="00002", name="Услуга Б", type=NomenclatureType.service
        )
        assert item.type == NomenclatureType.service

    def test_full_name_default_empty(self) -> None:
        item = NomenclatureItem(guid="g", code="c", name="n")
        assert item.full_name == ""


class TestWarehouse:
    def test_basic(self) -> None:
        wh = Warehouse(guid="wh-1", code="001", name="Основной склад", is_main=True)
        assert wh.is_main
        assert wh.code == "001"

    def test_not_main_by_default(self) -> None:
        wh = Warehouse(guid="wh-2", code="002", name="Доп склад")
        assert not wh.is_main


class TestCounterparty:
    def test_customer_by_default(self) -> None:
        cp = Counterparty(guid="cp-1", code="0001", name="ООО Ромашка", inn="7712345678")
        assert cp.is_customer
        assert not cp.is_supplier
        assert cp.inn == "7712345678"

    def test_supplier(self) -> None:
        cp = Counterparty(
            guid="cp-2", code="0002", name="ИП Иванов", is_customer=False, is_supplier=True
        )
        assert cp.is_supplier


class TestSalesOrder:
    def test_defaults(self) -> None:
        order = SalesOrder(
            guid="ord-1", number="ЗП-000001", date="2026-05-28", counterparty_guid="cp-1"
        )
        assert order.status == OrderStatus.draft
        assert order.lines == []

    def test_with_lines(self) -> None:
        line = OrderLine(
            line_number=1,
            nomenclature_guid="nom-1",
            quantity=Decimal("10"),
            price=Decimal("100.00"),
            amount=Decimal("1000.00"),
        )
        order = SalesOrder(
            guid="ord-2",
            number="ЗП-000002",
            date="2026-05-28",
            counterparty_guid="cp-1",
            lines=[line],
        )
        assert len(order.lines) == 1
        assert order.lines[0].amount == Decimal("1000.00")
