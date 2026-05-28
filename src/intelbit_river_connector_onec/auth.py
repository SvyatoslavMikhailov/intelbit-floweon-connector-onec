"""Аутентификация 1С: Basic, OAuth2 Client Credentials, mTLS (stub)."""

from dataclasses import dataclass
from enum import StrEnum


class AuthType(StrEnum):
    basic = "basic"
    oauth2 = "oauth2"
    mtls = "mtls"


@dataclass
class OneCAuth:
    """Параметры аутентификации для подключения к 1С."""

    type: AuthType
    username: str = ""
    password: str = ""
    token_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    cert_path: str = ""
    key_path: str = ""

    async def get_token(self) -> str:
        """Получить Bearer-токен (OAuth2) или Basic-заголовок."""
        raise NotImplementedError
