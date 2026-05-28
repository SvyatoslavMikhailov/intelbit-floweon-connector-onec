"""ODATA-клиент для 1С (stub)."""

from typing import Any


class OneCODataClient:
    """Чтение данных 1С через стандартный ODATA-интерфейс.

    Stub — реализация в фазе 3 MVP.
    """

    def __init__(self, base_url: str, auth_header: str) -> None:
        self.base_url = base_url
        self.auth_header = auth_header

    async def query(
        self, entity: str, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Выборка сущностей через ODATA $filter."""
        raise NotImplementedError

    async def get(self, entity: str, key: str) -> dict[str, Any]:
        """Получение одной записи по ключу (GUID)."""
        raise NotImplementedError
