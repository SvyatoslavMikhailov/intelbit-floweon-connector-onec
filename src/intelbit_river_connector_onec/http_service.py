"""Клиент HTTPСервисов 1С (stub)."""

from typing import Any


class OneCHttpServiceClient:
    """Вызов HTTPСервисов, опубликованных в 1С.

    Stub — реализация в фазе 3 MVP.
    """

    def __init__(self, base_url: str, auth_header: str) -> None:
        self.base_url = base_url
        self.auth_header = auth_header

    async def call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Вызов HTTPСервиса 1С."""
        raise NotImplementedError
