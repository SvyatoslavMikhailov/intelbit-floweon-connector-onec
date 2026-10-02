"""OneCConnector — реальная реализация коннектора 1С для Интелбит.Фловеон."""

from __future__ import annotations

from typing import Any

import httpx

from intelbit_floweon_connector_onec.auth import BasicAuth, OAuthClientCredentials, OneCAuth
from intelbit_floweon_connector_onec.enterprise_data import EnterpriseDataClient
from intelbit_floweon_connector_onec.http_service import OneCHttpServiceClient
from intelbit_floweon_connector_onec.models import SalesOrder
from intelbit_floweon_connector_onec.odata import OneCODataClient
from intelbit_floweon_connector_onec.webhooks import OneCWebhookReceiver

# Сущности, читаемые через OData (быстрее, чем EnterpriseData)
_ODATA_ENTITIES = frozenset(["Номенклатура", "Контрагент", "Склад"])


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
        self._ed = EnterpriseDataClient(
            config.get("enterprise_data", {"base_url": "http://localhost/ed"}), auth
        )
        self._http = OneCHttpServiceClient(
            config.get("http_service", {"base_url": "http://localhost/api"}),
            auth,
            _transport=_transport,
        )
        self._odata = OneCODataClient(
            config.get("odata", {"base_url": "http://localhost/odata/standard.odata"}),
            auth,
            _transport=_transport,
        )
        self._webhooks = OneCWebhookReceiver(
            config.get("webhooks", {"webhook_secret": "dev-secret"})
        )

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
                clauses = [f"{k} eq '{v}'" for k, v in filter.items()]
                odata_filter = " and ".join(clauses)
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
        self._webhooks.verify_signature(headers, body)
        return self._webhooks.parse_event(body)
