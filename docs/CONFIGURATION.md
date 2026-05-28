# Конфигурация коннектора 1С

## Параметры

| Параметр | Тип | Обязательный | Описание |
|---|---|---|---|
| `base_url` | string | да | URL базы 1С (`http://server/base`) |
| `auth_type` | enum | да | `basic` / `oauth2` / `mtls` |
| `username` | string | basic | Пользователь 1С |
| `password` | string | basic | Пароль |
| `token_url` | string | oauth2 | URL OAuth2 token endpoint |
| `client_id` | string | oauth2 | Client ID |
| `client_secret` | string | oauth2 | Client Secret |
| `cert_path` | string | mtls | Путь к сертификату клиента |
| `key_path` | string | mtls | Путь к приватному ключу |
| `timeout` | int | нет | Таймаут HTTP (сек), default 30 |
| `verify_ssl` | bool | нет | Проверка SSL, default true |

## Пример конфига в preset.yaml

```yaml
connectors:
  onec:
    plugin: intelbit-river-connector-onec
    version: ">=0.1.0"
    config:
      base_url: "http://1c-server.company.ru/UT11"
      auth_type: basic
      username: "river_user"
      password: "${secrets.ONEC_PASSWORD}"
      timeout: 60
```
