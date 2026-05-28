"""Тесты аутентификации: BasicAuth, OAuthClientCredentials."""

import base64
import time

import pytest
from pytest_httpx import HTTPXMock

from intelbit_river_connector_onec.auth import BasicAuth, OAuthClientCredentials


class TestBasicAuth:
    @pytest.mark.asyncio
    async def test_basic_auth_header_format(self) -> None:
        auth = BasicAuth("admin", "secret123")
        headers = await auth.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    @pytest.mark.asyncio
    async def test_basic_auth_credentials_encoded(self) -> None:
        auth = BasicAuth("user1С", "пароль")
        headers = await auth.get_headers()
        token = headers["Authorization"].removeprefix("Basic ")
        decoded = base64.b64decode(token).decode()
        assert decoded == "user1С:пароль"

    @pytest.mark.asyncio
    async def test_basic_auth_empty_password(self) -> None:
        auth = BasicAuth("admin", "")
        headers = await auth.get_headers()
        token = headers["Authorization"].removeprefix("Basic ")
        decoded = base64.b64decode(token).decode()
        assert decoded == "admin:"


class TestOAuthClientCredentials:
    @pytest.mark.asyncio
    async def test_fetch_token_on_first_call(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://auth.example.com/token",
            json={"access_token": "tok-abc123", "expires_in": 3600},
        )
        auth = OAuthClientCredentials("client1", "secret1", "https://auth.example.com/token")
        headers = await auth.get_headers()
        assert headers["Authorization"] == "Bearer tok-abc123"

    @pytest.mark.asyncio
    async def test_token_cached_on_second_call(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://auth.example.com/token",
            json={"access_token": "tok-cached", "expires_in": 3600},
        )
        auth = OAuthClientCredentials("c", "s", "https://auth.example.com/token")
        await auth.get_headers()
        # Второй вызов не должен делать запрос (mock вернул бы ошибку если дёрнуть снова)
        headers = await auth.get_headers()
        assert headers["Authorization"] == "Bearer tok-cached"

    @pytest.mark.asyncio
    async def test_token_refreshed_when_expired(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://auth.example.com/token",
            json={"access_token": "tok-new", "expires_in": 3600},
        )
        auth = OAuthClientCredentials("c", "s", "https://auth.example.com/token")
        # Имитируем истёкший токен
        auth._access_token = "tok-old"
        auth._expires_at = time.monotonic() - 1  # уже истёк
        headers = await auth.get_headers()
        assert headers["Authorization"] == "Bearer tok-new"
