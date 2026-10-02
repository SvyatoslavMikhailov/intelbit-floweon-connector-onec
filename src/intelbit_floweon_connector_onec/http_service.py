"""Клиент HTTPСервисов 1С: async httpx + tenacity retry + Idempotency-Key."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from intelbit_floweon_connector_onec.auth import OneCAuth

_USER_AGENT = "intelbit-floweon-connector-onec/0.2.0"


class OneCHttpServiceError(Exception):
    """Ошибка HTTP-вызова к 1С с расшифрованным кодом из тела ответа."""

    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        super().__init__(f"1C HTTP error {status_code} [{error_code}]: {message}")
        self.status_code = status_code
        self.error_code = error_code
        self.onec_message = message


class OneCHttpServiceClient:
    """Async-клиент HTTPСервисов 1С с retry и idempotency."""

    def __init__(
        self,
        config: dict[str, Any],
        auth: OneCAuth,
        _transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = config["base_url"].rstrip("/")
        self._timeout: float = float(config.get("timeout", 30.0))
        self._auth = auth
        self._transport = _transport

    async def call(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Вызов HTTPСервиса 1С. Non-GET запросы получают Idempotency-Key."""
        headers = await self._auth.get_headers()
        headers["Accept"] = "application/json"
        headers["User-Agent"] = _USER_AGENT
        if method.upper() != "GET":
            headers["Idempotency-Key"] = str(uuid.uuid4())

        return await self._call_with_retry(method, path, payload, headers)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(
            lambda e: not (isinstance(e, OneCHttpServiceError) and e.status_code < 500)
        ),
        reraise=True,
    )
    async def _call_with_retry(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.request(
                method,
                url,
                json=payload,
                headers=headers,
            )

        if response.status_code >= 400:
            self._raise_onec_error(response)

        result: dict[str, Any] = response.json()
        return result

    @staticmethod
    def _raise_onec_error(response: httpx.Response) -> None:
        try:
            body: dict[str, Any] = response.json()
            err = body.get("error", {})
            code: str = str(err.get("code", str(response.status_code)))
            message: str = str(err.get("message", response.text))
        except Exception:
            code = str(response.status_code)
            message = response.text
        raise OneCHttpServiceError(response.status_code, code, message)
