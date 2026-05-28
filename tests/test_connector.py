"""Тесты skeleton OneCConnector — все методы должны поднимать NotImplementedError."""

import pytest

from intelbit_river_connector_onec.connector import OneCConnector
from intelbit_river_connector_onec.models import OrderStatus, SalesOrder


@pytest.fixture
def connector() -> OneCConnector:
    return OneCConnector(config={"base_url": "http://localhost/1c", "auth_type": "basic"})


@pytest.fixture
def sample_order() -> SalesOrder:
    return SalesOrder(
        guid="ord-1",
        number="ЗП-000001",
        date="2026-05-28",
        counterparty_guid="cp-1",
        status=OrderStatus.draft,
    )


class TestOneCConnectorStubs:
    @pytest.mark.asyncio
    async def test_read_catalog_raises(self, connector: OneCConnector) -> None:
        with pytest.raises(NotImplementedError):
            await connector.read_catalog("Номенклатура")

    @pytest.mark.asyncio
    async def test_write_order_raises(
        self, connector: OneCConnector, sample_order: SalesOrder
    ) -> None:
        with pytest.raises(NotImplementedError):
            await connector.write_order(sample_order)

    @pytest.mark.asyncio
    async def test_get_nomenclature_raises(self, connector: OneCConnector) -> None:
        with pytest.raises(NotImplementedError):
            await connector.get_nomenclature("some-guid")

    @pytest.mark.asyncio
    async def test_get_counterparty_raises(self, connector: OneCConnector) -> None:
        with pytest.raises(NotImplementedError):
            await connector.get_counterparty("7712345678")

    @pytest.mark.asyncio
    async def test_get_warehouses_raises(self, connector: OneCConnector) -> None:
        with pytest.raises(NotImplementedError):
            await connector.get_warehouses()

    @pytest.mark.asyncio
    async def test_health_check_raises(self, connector: OneCConnector) -> None:
        with pytest.raises(NotImplementedError):
            await connector.health_check()

    def test_config_stored(self, connector: OneCConnector) -> None:
        assert connector.config["base_url"] == "http://localhost/1c"
