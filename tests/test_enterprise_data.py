"""Тесты EnterpriseData XML-клиента и схем сущностей."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree
from pytest_httpx import HTTPXMock

from intelbit_floweon_connector_onec.auth import BasicAuth
from intelbit_floweon_connector_onec.enterprise_data import EnterpriseDataClient
from intelbit_floweon_connector_onec.enterprise_data_schema import (
    NS,
    EDCounterparty,
    EDNomenclature,
    EDNomenclaturePrice,
    EDNomenclatureStock,
    EDSalesOrder,
    EDSalesOrderLine,
    EDWarehouse,
)

FIXTURES = Path(__file__).parent / "fixtures" / "onec-mocks" / "enterprise_data"


def _make_client(httpx_mock: HTTPXMock) -> EnterpriseDataClient:
    auth = BasicAuth("admin", "pass")
    config = {
        "base_url": "https://1c.example.com",
        "plan": "ОсновнойПланОбмена",
        "node": "ЦентральныйУзел",
    }
    return EnterpriseDataClient(config, auth)


# ---------------------------------------------------------------------------
# Тесты схем XML-сериализации
# ---------------------------------------------------------------------------


class TestEDNomenclature:
    def test_to_xml_fields(self) -> None:
        nom = EDNomenclature(
            ref_key="abc-001",
            code="001",
            description="Ноутбук",
            full_description="Ноутбук Dell",
            nomenclature_type="Товар",
            unit_of_measure="шт",
            vat_rate="НДС20",
        )
        elem = nom.to_xml()
        assert elem.tag == f"{{{NS}}}Catalog.Номенклатура"
        ref = elem.find(f"{{{NS}}}Ref_Key")
        assert ref is not None and ref.text == "abc-001"
        desc = elem.find(f"{{{NS}}}Description")
        assert desc is not None and desc.text == "Ноутбук"

    def test_from_xml_round_trip(self) -> None:
        nom = EDNomenclature(
            ref_key="abc-002",
            code="002",
            description="Мышь",
            unit_of_measure="шт",
        )
        elem = nom.to_xml()
        restored = EDNomenclature.from_xml(elem)
        assert restored.ref_key == nom.ref_key
        assert restored.description == nom.description
        assert restored.unit_of_measure == nom.unit_of_measure

    def test_from_xml_is_archived(self) -> None:
        nom = EDNomenclature(ref_key="x", code="x", description="x", is_archived=True)
        elem = nom.to_xml()
        restored = EDNomenclature.from_xml(elem)
        assert restored.is_archived is True


class TestEDCounterparty:
    def test_round_trip(self) -> None:
        cp = EDCounterparty(
            ref_key="cp-001",
            code="К001",
            description="ООО Тест",
            inn="7701234567",
            kpp="770101001",
            is_customer=True,
            is_supplier=False,
        )
        elem = cp.to_xml()
        restored = EDCounterparty.from_xml(elem)
        assert restored.inn == "7701234567"
        assert restored.is_supplier is False


class TestEDWarehouse:
    def test_round_trip(self) -> None:
        wh = EDWarehouse(ref_key="wh-001", code="СК001", description="Основной склад", is_main=True)
        elem = wh.to_xml()
        restored = EDWarehouse.from_xml(elem)
        assert restored.is_main is True
        assert restored.description == "Основной склад"


class TestEDSalesOrder:
    def test_round_trip_with_lines(self) -> None:
        order = EDSalesOrder(
            ref_key="ord-001",
            number="Ш000001",
            date="2026-05-28T00:00:00",
            lines=[
                EDSalesOrderLine(
                    line_number=1,
                    nomenclature_key="nom-001",
                    quantity=Decimal("2"),
                    price=Decimal("89990"),
                    amount=Decimal("179980"),
                )
            ],
        )
        elem = order.to_xml()
        restored = EDSalesOrder.from_xml(elem)
        assert restored.number == "Ш000001"
        assert len(restored.lines) == 1
        assert restored.lines[0].quantity == Decimal("2")


class TestEDPrice:
    def test_round_trip(self) -> None:
        price = EDNomenclaturePrice(
            nomenclature_key="nom-001",
            price_type_key="pt-001",
            price=Decimal("89990.00"),
            currency="RUB",
        )
        elem = price.to_xml()
        restored = EDNomenclaturePrice.from_xml(elem)
        assert restored.price == Decimal("89990.00")
        assert restored.currency == "RUB"


class TestEDStock:
    def test_round_trip(self) -> None:
        stock = EDNomenclatureStock(
            nomenclature_key="nom-001",
            warehouse_key="wh-001",
            quantity=Decimal("15"),
            reserved=Decimal("2"),
        )
        elem = stock.to_xml()
        restored = EDNomenclatureStock.from_xml(elem)
        assert restored.quantity == Decimal("15")
        assert restored.reserved == Decimal("2")


# ---------------------------------------------------------------------------
# Тесты HTTP-клиента EnterpriseDataClient
# ---------------------------------------------------------------------------


class TestEnterpriseDataClient:
    @pytest.mark.asyncio
    async def test_receive_parses_nomenclature_xml(self, httpx_mock: HTTPXMock) -> None:
        xml_bytes = (FIXTURES / "Номенклатура_УТ11_5.xml").read_bytes()
        httpx_mock.add_response(
            url="https://1c.example.com/exchange/ОсновнойПланОбмена/ЦентральныйУзел",
            content=xml_bytes,
        )
        client = _make_client(httpx_mock)
        messages = await client.receive_messages()
        assert len(messages) == 1
        assert len(messages[0].entities) == 5
        assert messages[0].entities[0]["description"] == "Ноутбук Dell XPS 13"

    @pytest.mark.asyncio
    async def test_receive_parses_counterparty_xml(self, httpx_mock: HTTPXMock) -> None:
        xml_bytes = (FIXTURES / "Контрагент_УТ11_5.xml").read_bytes()
        httpx_mock.add_response(
            url="https://1c.example.com/exchange/ОсновнойПланОбмена/ЦентральныйУзел",
            content=xml_bytes,
        )
        client = _make_client(httpx_mock)
        messages = await client.receive_messages()
        assert len(messages[0].entities) == 3
        assert messages[0].entities[0]["inn"] == "7701234567"

    @pytest.mark.asyncio
    async def test_send_message_returns_uuid(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://1c.example.com/exchange/ОсновнойПланОбмена/ЦентральныйУзел",
            status_code=200,
        )
        client = _make_client(httpx_mock)
        entities = [{"__type__": "Catalog.Номенклатура", "Ref_Key": "x", "Description": "Тест"}]
        msg_id = await client.send_message(entities)
        assert re.match(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", msg_id)

    @pytest.mark.asyncio
    async def test_send_message_xml_contains_namespace(self, httpx_mock: HTTPXMock) -> None:
        sent_body: list[bytes] = []

        def capture(request: object, extensions: object) -> None:
            import httpx as _httpx

            if isinstance(request, _httpx.Request):
                sent_body.append(request.content)

        httpx_mock.add_response(status_code=200)
        client = _make_client(httpx_mock)
        await client.send_message([{"__type__": "Catalog.Номенклатура", "Ref_Key": "y"}])
        requests = httpx_mock.get_requests()
        body = requests[0].content
        assert b"urn:1C.ru:EnterpriseData:1.5" in body

    @pytest.mark.asyncio
    async def test_receive_invalid_xml_raises(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(content=b"<not valid xml>>>")
        client = _make_client(httpx_mock)
        with pytest.raises(etree.XMLSyntaxError):
            await client.receive_messages()

    @pytest.mark.asyncio
    async def test_send_cyrillic_encoded_as_utf8(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=200)
        client = _make_client(httpx_mock)
        await client.send_message(
            [{"__type__": "Catalog.Номенклатура", "Description": "Товар с кириллицей"}]
        )
        body = httpx_mock.get_requests()[0].content
        assert "Товар с кириллицей".encode() in body
