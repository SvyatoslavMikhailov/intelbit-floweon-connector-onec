"""OneCConnector — коннектор 1С для Интелбит:Река.

Реализует контракт Connector из intelbit-river-sdk (ADR-006).
Стадия: skeleton (v0.0.1). Реализация — фаза 3 MVP.
"""

from typing import Any

from intelbit_river_connector_onec.models import (
    Counterparty,
    NomenclatureItem,
    SalesOrder,
    Warehouse,
)


class OneCConnector:
    """Коннектор 1С (УТ 11.5, КА 2.5, ERP 2.5).

    Все методы — NotImplementedError. Реализация в фазе 3.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def read_catalog(self, entity_type: str) -> list[dict[str, Any]]:
        """Чтение каталога из 1С через EnterpriseData или ODATA."""
        raise NotImplementedError

    async def write_order(self, order: SalesOrder) -> str:
        """Запись заказа покупателя в 1С. Возвращает GUID."""
        raise NotImplementedError

    async def get_nomenclature(self, guid: str) -> NomenclatureItem:
        """Получение номенклатуры по GUID."""
        raise NotImplementedError

    async def get_counterparty(self, inn: str) -> Counterparty:
        """Поиск контрагента по ИНН."""
        raise NotImplementedError

    async def get_warehouses(self) -> list[Warehouse]:
        """Список складов."""
        raise NotImplementedError

    async def health_check(self) -> bool:
        """Проверка доступности 1С (HTTP ping)."""
        raise NotImplementedError
