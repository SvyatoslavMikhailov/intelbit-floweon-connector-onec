"""EnterpriseData HTTP-клиент для 1С (stub)."""

from typing import Any


class EnterpriseDataClient:
    """Клиент протокола EnterpriseData (формат обмена 1С).

    Stub — реализация в фазе 3 MVP.
    """

    def __init__(self, base_url: str, auth_header: str) -> None:
        self.base_url = base_url
        self.auth_header = auth_header

    async def upload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Отправка данных в 1С через EnterpriseData."""
        raise NotImplementedError

    async def download(self, message_id: str) -> dict[str, Any]:
        """Получение данных из 1С через EnterpriseData."""
        raise NotImplementedError
