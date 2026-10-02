"""Webhook-receiver: HMAC-SHA256 проверка подписи, replay-защита, dedup через Redis."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

from intelbit_floweon_connector_onec.exceptions import ConfigurationError

# Минимальная длина общего секрета HMAC: короче — подбирается/угадывается.
MIN_SECRET_LENGTH = 16


class WebhookSignatureError(ValueError):
    """Ошибка проверки подписи входящего webhook."""


SUPPORTED_EVENTS = frozenset(
    ["catalog.updated", "stock.updated", "price.updated", "order.status.changed"]
)


class OneCWebhookReceiver:
    """Проверка и разбор входящих webhook-событий от 1С."""

    def __init__(self, config: dict[str, Any]) -> None:
        secret = config.get("webhook_secret")
        if not isinstance(secret, str) or not secret.strip():
            raise ConfigurationError(
                "Не задан webhooks.webhook_secret (обязателен при webhooks.enabled=true)"
            )
        if len(secret) < MIN_SECRET_LENGTH:
            # Длину называем, значение — никогда.
            raise ConfigurationError(f"webhooks.webhook_secret короче {MIN_SECRET_LENGTH} символов")
        self._secret: str = secret
        self._replay_window: int = int(config.get("replay_window_sec", 300))

    def verify_signature(self, headers: dict[str, str], body: bytes) -> None:
        """Проверить X-Signature: t=<unix>,v1=<hex>.

        Поднимает WebhookSignatureError при неверной подписи или replay-атаке.
        """
        sig_header = headers.get("X-Signature") or headers.get("x-signature") or ""
        if not sig_header:
            raise WebhookSignatureError("Заголовок X-Signature отсутствует")

        parts: dict[str, str] = {}
        for chunk in sig_header.split(","):
            k, _, v = chunk.partition("=")
            parts[k.strip()] = v.strip()

        timestamp_str = parts.get("t", "")
        v1 = parts.get("v1", "")
        if not timestamp_str or not v1:
            raise WebhookSignatureError("X-Signature: отсутствует t или v1")

        try:
            timestamp = int(timestamp_str)
        except ValueError as exc:
            raise WebhookSignatureError("X-Signature: t не является целым числом") from exc

        now = int(time.time())
        if abs(now - timestamp) > self._replay_window:
            raise WebhookSignatureError(
                f"Replay-атака: разница времени {abs(now - timestamp)}s > {self._replay_window}s"
            )

        payload = f"{timestamp_str}.".encode() + body
        expected = hmac.new(self._secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, v1):
            raise WebhookSignatureError("X-Signature: неверный HMAC-SHA256")

    def deduplicate(self, event_id: str, redis_client: Any) -> bool:
        """Проверить уникальность события через Redis SET NX.

        Возвращает True если событие новое, False если дубликат.
        """
        key = f"webhook:dedup:{event_id}"
        result = redis_client.set(key, "1", nx=True, ex=86400)
        return result is not None

    def parse_event(self, body: bytes) -> dict[str, Any]:
        """Разобрать тело webhook-события с валидацией типа."""
        try:
            data: dict[str, Any] = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Невалидный JSON в теле webhook: {exc}") from exc

        event_type: str = data.get("event_type", "")
        if event_type not in SUPPORTED_EVENTS:
            raise ValueError(f"Неподдерживаемый тип события: {event_type!r}")

        return data
