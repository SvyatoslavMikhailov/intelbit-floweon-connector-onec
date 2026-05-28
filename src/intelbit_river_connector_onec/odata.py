"""Read-only OData-клиент для стандартного OData REST 1С."""

from __future__ import annotations

from typing import Any

import httpx

from intelbit_river_connector_onec.auth import OneCAuth


class OneCODataClient:
    """Чтение данных 1С через стандартный OData-интерфейс (только чтение)."""

    def __init__(self, config: dict[str, Any], auth: OneCAuth) -> None:
        self._base_url = config["base_url"].rstrip("/")
        self._timeout: float = float(config.get("timeout", 30.0))
        self._auth = auth

    async def query(
        self,
        entity: str,
        filter: str | None = None,
        top: int = 100,
        skip: int = 0,
        orderby: str | None = None,
        expand: str | None = None,
    ) -> list[dict[str, Any]]:
        """Выборка записей с $filter / $top / $skip / $orderby / $expand."""
        params: dict[str, str] = {
            "$top": str(top),
            "$skip": str(skip),
            "$format": "json",
        }
        if filter:
            params["$filter"] = filter
        if orderby:
            params["$orderby"] = orderby
        if expand:
            params["$expand"] = expand

        headers = await self._auth.get_headers()
        headers["Accept"] = "application/json"
        url = f"{self._base_url}/{entity}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

        data: dict[str, Any] = response.json()
        result: list[dict[str, Any]] = data.get("value", [])
        return result

    async def get(self, entity: str, key: str) -> dict[str, Any] | None:
        """Получить запись по GUID-ключу (формат Catalog_Номенклатура(guid'...')"""
        headers = await self._auth.get_headers()
        headers["Accept"] = "application/json"
        url = f"{self._base_url}/{entity}(guid'{key}')"
        params = {"$format": "json"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()

        result: dict[str, Any] = response.json()
        return result
