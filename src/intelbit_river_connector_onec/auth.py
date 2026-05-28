"""Аутентификация для клиентов 1С: Basic и OAuth 2.1 Client Credentials."""

import base64
import time
from typing import Any

import httpx


class OneCAuth:
    """Базовый класс аутентификации."""

    async def get_headers(self) -> dict[str, str]:
        raise NotImplementedError


class BasicAuth(OneCAuth):
    """HTTP Basic Auth для dev-окружений."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    async def get_headers(self) -> dict[str, str]:
        credentials = f"{self._username}:{self._password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}


class OAuthClientCredentials(OneCAuth):
    """OAuth 2.1 Client Credentials с авто-рефрешем токена."""

    def __init__(self, client_id: str, client_secret: str, token_url: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    async def get_headers(self) -> dict[str, str]:
        if self._is_expired():
            await self._fetch_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    def _is_expired(self) -> bool:
        # рефреш за 30 секунд до истечения
        return self._access_token is None or time.monotonic() >= self._expires_at - 30

    async def _fetch_token(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        self._access_token = data["access_token"]
        expires_in: int = int(data.get("expires_in", 3600))
        self._expires_at = time.monotonic() + expires_in
