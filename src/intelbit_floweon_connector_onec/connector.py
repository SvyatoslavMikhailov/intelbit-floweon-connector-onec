"""OneCConnector — реальная реализация коннектора 1С для Интелбит.Фловеон."""

from __future__ import annotations

import re
from typing import Any

import httpx

from intelbit_floweon_connector_onec.auth import BasicAuth, OAuthClientCredentials, OneCAuth
from intelbit_floweon_connector_onec.enterprise_data import EnterpriseDataClient
from intelbit_floweon_connector_onec.exceptions import ConfigurationError
from intelbit_floweon_connector_onec.http_service import OneCHttpServiceClient
from intelbit_floweon_connector_onec.models import SalesOrder
from intelbit_floweon_connector_onec.odata import OneCODataClient
from intelbit_floweon_connector_onec.webhooks import OneCWebhookReceiver, WebhookSignatureError

# Сущности, читаемые через OData (быстрее, чем EnterpriseData)
_ODATA_ENTITIES = frozenset(["Номенклатура", "Контрагент", "Склад"])

# Имя свойства OData в $filter: буква или «_», далее буквы/цифры/«_». Буквы —
# Unicode: реквизиты 1С бывают кириллическими (Артикул). Пробелы, кавычки,
# скобки и операторы исключены — это закрывает инъекцию через ключ фильтра.
_ODATA_KEY_RE = re.compile(r"^[^\W\d]\w*$")


def _require_section(config: dict[str, Any], section: str) -> dict[str, Any]:
    """Вернуть секцию конфига с непустым base_url, иначе ConfigurationError."""
    value = config.get(section)
    if not isinstance(value, dict) or not str(value.get("base_url") or "").strip():
        raise ConfigurationError(f"Не задан обязательный ключ {section}.base_url")
    return value


def _build_odata_filter(filter: dict[str, Any]) -> str:
    """Собрать OData $filter из пар ключ=значение с экранированием.

    Ключи проверяются по _ODATA_KEY_RE, в значениях одинарная кавычка
    удваивается (`'` → `''`) по правилам литералов OData.
    """
    clauses: list[str] = []
    for key, value in filter.items():
        if not isinstance(key, str) or not _ODATA_KEY_RE.match(key):
            raise ValueError(f"Недопустимое имя свойства OData в фильтре: {key!r}")
        escaped = str(value).replace("'", "''")
        clauses.append(f"{key} eq '{escaped}'")
    return " and ".join(clauses)


def _build_auth(auth_config: dict[str, Any]) -> OneCAuth:
    auth_type: str = auth_config.get("type", "basic")
    if auth_type == "oauth2":
        return OAuthClientCredentials(
            client_id=str(auth_config["client_id"]),
            client_secret=str(auth_config["client_secret"]),
            token_url=str(auth_config["token_url"]),
        )
    return BasicAuth(
        username=str(auth_config.get("username", "")),
        password=str(auth_config.get("password", "")),
    )


class OneCConnector:
    """Коннектор 1С (УТ 11.5, КА 2.5, ERP 2.5)."""

    def __init__(
        self,
        config: dict[str, Any],
        _transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        auth = _build_auth(config.get("auth", {}))
        # Fail-closed: без явных адресов 1С коннектор не стартует (раньше были
        # дефолты http://localhost/..., которые маскировали незаданный конфиг).
        self._ed = EnterpriseDataClient(_require_section(config, "enterprise_data"), auth)
        self._http = OneCHttpServiceClient(
            _require_section(config, "http_service"),
            auth,
            _transport=_transport,
        )
        self._odata = OneCODataClient(
            _require_section(config, "odata"),
            auth,
            _transport=_transport,
        )
        webhooks_config: dict[str, Any] = config.get("webhooks") or {}
        self._webhooks: OneCWebhookReceiver | None = None
        if webhooks_config.get("enabled", True):
            # Секрет проверяет сам OneCWebhookReceiver (непустой, ≥16 символов).
            self._webhooks = OneCWebhookReceiver(webhooks_config)

    async def read_catalog(
        self,
        entity_type: str,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Читать каталог из 1С: OData для справочников, ED для сложных сущностей."""
        if entity_type in _ODATA_ENTITIES:
            odata_entity = f"Catalog_{entity_type}"
            odata_filter: str | None = None
            if filter:
                odata_filter = _build_odata_filter(filter)
            return await self._odata.query(odata_entity, filter=odata_filter)

        messages = await self._ed.receive_messages()
        result: list[dict[str, Any]] = []
        for msg in messages:
            result.extend(msg.entities)
        return result

    async def create_order(self, order: SalesOrder) -> dict[str, Any]:
        """Создать заказ покупателя через HTTPСервис 1С."""
        payload = order.model_dump(mode="json")
        return await self._http.call("POST", "/api/orders/", payload)

    async def update_stocks(self, stocks: list[dict[str, Any]]) -> dict[str, Any]:
        """Отправить остатки в 1С через EnterpriseData (batch)."""
        entities = [{"__type__": "AccumulationRegister.ТоварыНаСкладах", **s} for s in stocks]
        message_id = await self._ed.send_message(entities)
        return {"message_id": message_id, "count": len(stocks)}

    async def update_prices(self, prices: list[dict[str, Any]]) -> dict[str, Any]:
        """Отправить цены в 1С через EnterpriseData (batch)."""
        entities = [{"__type__": "InformationRegister.ЦеныНоменклатуры", **p} for p in prices]
        message_id = await self._ed.send_message(entities)
        return {"message_id": message_id, "count": len(prices)}

    async def on_webhook(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        """Обработать входящий webhook от 1С: проверить подпись, распарсить событие."""
        if self._webhooks is None:
            # Приём выключен (webhooks.enabled=false) — любой запрос отклоняется.
            raise WebhookSignatureError("Приём webhook выключен (webhooks.enabled=false)")
        self._webhooks.verify_signature(headers, body)
        return self._webhooks.parse_event(body)
