# intelbit-river-connector-onec

Коннектор 1С (УТ 11.5, КА 2.5, ERP 2.5) для **Интелбит:Река** — открытой интеграционной шины данных для торговых компаний.

## Что умеет (v0.0.1 — скелет)

- Typed Pydantic-модели 1С-сущностей: Номенклатура, Заказ покупателя, Контрагент, Склад
- Skeleton `OneCConnector` по контракту ADR-006 (Plugin API)
- Заглушки EnterpriseData / HTTPСервисы / ODATA / Webhooks — реализация в фазе 3 MVP

## Что будет в v0.1.0 (MVP Реки)

- EnterpriseData чтение/запись (Номенклатура, Заказ, Контрагент)
- HTTPСервисы 1С для real-time-операций
- Webhook-receiver с HMAC-валидацией
- Поддержка УТ 11.5, КА 2.5, ERP 2.5 через общий слой

## Установка

```bash
pip install intelbit-river-connector-onec
```

## Быстрый старт

```python
from intelbit_river_connector_onec import OneCConnector

connector = OneCConnector(config={
    "base_url": "http://your-1c-server/base",
    "username": "river_user",
    "password": "secret",
})
# v0.0.1: методы — stubs, реализация в v0.1.0
```

## Конфигурация

Параметры подключения — в [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Связанные проекты

- **Интелбит:Река** — главный продукт, использующий этот коннектор
- [intelbit-river-monorepo](https://github.com/SvyatoslavMikhailov/intelbit-river-monorepo) — monorepo ядра Реки
