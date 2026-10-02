"""Коннектор 1С (УТ 11.5, КА 2.5, ERP 2.5) для Интелбит.Фловеон."""

from intelbit_floweon_connector_onec.connector import OneCConnector
from intelbit_floweon_connector_onec.exceptions import ConfigurationError
from intelbit_floweon_connector_onec.models import (
    Counterparty,
    NomenclatureItem,
    SalesOrder,
    Warehouse,
)

__version__ = "0.0.1"

__all__ = [
    "ConfigurationError",
    "Counterparty",
    "NomenclatureItem",
    "OneCConnector",
    "SalesOrder",
    "Warehouse",
]
