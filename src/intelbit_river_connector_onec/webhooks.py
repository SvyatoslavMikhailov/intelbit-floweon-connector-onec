"""Webhook-receiver для входящих событий 1С (stub)."""

from typing import Any


class OneCWebhookReceiver:
    """Приём событий от 1С через HTTP-обратный вызов.

    Stub — реализация в фазе 3 MVP.
    Предполагается HMAC-SHA256 валидация подписи.
    """

    def __init__(self, secret: str) -> None:
        self.secret = secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Проверка HMAC-подписи входящего события."""
        raise NotImplementedError

    async def handle(self, event_type: str, payload: dict[str, Any]) -> None:
        """Обработка события от 1С."""
        raise NotImplementedError
