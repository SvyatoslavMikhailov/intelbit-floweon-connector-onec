# intelbit-floweon-connector-onec

Коннектор 1С (УТ 11.5, КА 2.5, ERP 2.5) для **Интелбит.Фловеон** — открытой интеграционной шины данных для торговых компаний.

## Что умеет (v0.0.1 — скелет)

- Typed Pydantic-модели 1С-сущностей: Номенклатура, Заказ покупателя, Контрагент, Склад
- Skeleton `OneCConnector` по контракту ADR-006 (Plugin API)
- Заглушки EnterpriseData / HTTPСервисы / ODATA / Webhooks — реализация в фазе 3 MVP

## Что будет в v0.1.0 (MVP Фловеона)

- EnterpriseData чтение/запись (Номенклатура, Заказ, Контрагент)
- HTTPСервисы 1С для real-time-операций
- Webhook-receiver с HMAC-валидацией
- Поддержка УТ 11.5, КА 2.5, ERP 2.5 через общий слой

## Установка

```bash
pip install intelbit-floweon-connector-onec
```

## Быстрый старт

```python
from intelbit_floweon_connector_onec import OneCConnector

connector = OneCConnector(config={
    "base_url": "http://your-1c-server/base",
    "username": "floweon_user",
    "password": "secret",
})
# v0.0.1: методы — stubs, реализация в v0.1.0
```

## Конфигурация

Параметры подключения — в [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Связанные проекты

- **Интелбит.Фловеон** — главный продукт, использующий этот коннектор
- [intelbit-floweon-monorepo](https://github.com/SvyatoslavMikhailov/intelbit-floweon-monorepo) — monorepo ядра Фловеона
