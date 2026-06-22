# Архитектура коннектора 1С

## Опорные документы

- **ADR-006** — Plugin API contract и SDK. Определяет базовый lifecycle и Connector ABC.
- **D-5 §1.3** — Объём MVP: УТ 11.5, КА 2.5, ERP 2.5 через общий слой.
- **ADR-001** — Архитектура Реки. Плагины — L4 модели расширений.

## Протоколы интеграции с 1С

| Протокол | Модуль | Статус |
|---|---|---|
| EnterpriseData | `enterprise_data.py` | Stub (фаза 3) |
| HTTPСервисы 1С | `http_service.py` | Stub (фаза 3) |
| ODATA | `odata.py` | Stub (фаза 3) |
| Webhook (обратный вызов) | `webhooks.py` | Stub (фаза 3) |

## Аутентификация

- Basic Auth — для dev/test 1С
- OAuth2 Client Credentials — для prod
- mTLS — опционально для enterprise

## Поддерживаемые конфигурации 1С

- 1С:Управление торговлей 11.5 (базовый таргет)
- 1С:Комплексная автоматизация 2.5 (общий слой с УТ 11.5)
- 1С:ERP 2.5 — через тот же слой с заглушками производственных полей

## Подключение river-sdk

Этот коннектор пока не зависит от `river-sdk`. При будущей привязке использовать **публичный git-тег** `intelbit-river-sdk @ vX.Y.Z` (репозиторий `SvyatoslavMikhailov/intelbit-river-sdk`), **не** path в приватный `intelbit-river-monorepo`.
