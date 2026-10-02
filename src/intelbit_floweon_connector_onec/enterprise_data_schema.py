"""Pydantic-схемы и XML-сериализация для сущностей EnterpriseData 1.5 (УТ 11.5)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from lxml import etree
from pydantic import BaseModel

NS = "urn:1C.ru:EnterpriseData:1.5"


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def _text(elem: etree._Element, name: str) -> str:
    child = elem.find(_tag(name))
    if child is None or child.text is None:
        return ""
    return child.text


def _sub(parent: etree._Element, name: str, text: str) -> None:
    etree.SubElement(parent, _tag(name)).text = text


class EDNomenclature(BaseModel):
    """Номенклатура (Catalog.Номенклатура)."""

    ref_key: str
    code: str
    description: str
    full_description: str = ""
    nomenclature_type: str = "Товар"
    unit_of_measure: str = "шт"
    vat_rate: str = "НДС20"
    is_archived: bool = False

    def to_xml(self) -> etree._Element:
        elem = etree.Element(_tag("Catalog.Номенклатура"))
        _sub(elem, "Ref_Key", self.ref_key)
        _sub(elem, "Code", self.code)
        _sub(elem, "Description", self.description)
        _sub(elem, "НаименованиеПолное", self.full_description)
        _sub(elem, "ВидНоменклатуры", self.nomenclature_type)
        _sub(elem, "ЕдиницаИзмерения", self.unit_of_measure)
        _sub(elem, "СтавкаНДС", self.vat_rate)
        _sub(elem, "DeletionMark", str(self.is_archived).lower())
        return elem

    @classmethod
    def from_xml(cls, elem: etree._Element) -> EDNomenclature:
        return cls(
            ref_key=_text(elem, "Ref_Key"),
            code=_text(elem, "Code"),
            description=_text(elem, "Description"),
            full_description=_text(elem, "НаименованиеПолное"),
            nomenclature_type=_text(elem, "ВидНоменклатуры") or "Товар",
            unit_of_measure=_text(elem, "ЕдиницаИзмерения") or "шт",
            vat_rate=_text(elem, "СтавкаНДС") or "НДС20",
            is_archived=_text(elem, "DeletionMark") == "true",
        )


class EDCounterparty(BaseModel):
    """Контрагент (Catalog.Контрагенты)."""

    ref_key: str
    code: str
    description: str
    inn: str = ""
    kpp: str = ""
    is_customer: bool = True
    is_supplier: bool = False
    is_archived: bool = False

    def to_xml(self) -> etree._Element:
        elem = etree.Element(_tag("Catalog.Контрагенты"))
        _sub(elem, "Ref_Key", self.ref_key)
        _sub(elem, "Code", self.code)
        _sub(elem, "Description", self.description)
        _sub(elem, "ИНН", self.inn)
        _sub(elem, "КПП", self.kpp)
        _sub(elem, "ЭтоПокупатель", str(self.is_customer).lower())
        _sub(elem, "ЭтоПоставщик", str(self.is_supplier).lower())
        _sub(elem, "DeletionMark", str(self.is_archived).lower())
        return elem

    @classmethod
    def from_xml(cls, elem: etree._Element) -> EDCounterparty:
        return cls(
            ref_key=_text(elem, "Ref_Key"),
            code=_text(elem, "Code"),
            description=_text(elem, "Description"),
            inn=_text(elem, "ИНН"),
            kpp=_text(elem, "КПП"),
            is_customer=_text(elem, "ЭтоПокупатель") != "false",
            is_supplier=_text(elem, "ЭтоПоставщик") == "true",
            is_archived=_text(elem, "DeletionMark") == "true",
        )


class EDWarehouse(BaseModel):
    """Склад (Catalog.Склады)."""

    ref_key: str
    code: str
    description: str
    is_main: bool = False
    is_archived: bool = False

    def to_xml(self) -> etree._Element:
        elem = etree.Element(_tag("Catalog.Склады"))
        _sub(elem, "Ref_Key", self.ref_key)
        _sub(elem, "Code", self.code)
        _sub(elem, "Description", self.description)
        _sub(elem, "ОсновнойСклад", str(self.is_main).lower())
        _sub(elem, "DeletionMark", str(self.is_archived).lower())
        return elem

    @classmethod
    def from_xml(cls, elem: etree._Element) -> EDWarehouse:
        return cls(
            ref_key=_text(elem, "Ref_Key"),
            code=_text(elem, "Code"),
            description=_text(elem, "Description"),
            is_main=_text(elem, "ОсновнойСклад") == "true",
            is_archived=_text(elem, "DeletionMark") == "true",
        )


class EDSalesOrderLine(BaseModel):
    """Строка заказа покупателя."""

    line_number: int
    nomenclature_key: str
    quantity: Decimal
    price: Decimal
    amount: Decimal
    vat_amount: Decimal = Decimal("0")


class EDSalesOrder(BaseModel):
    """ЗаказКлиента (Document.ЗаказКлиента)."""

    ref_key: str
    number: str
    date: str
    status: str = "НеСогласован"
    counterparty_key: str = ""
    warehouse_key: str = ""
    comment: str = ""
    lines: list[EDSalesOrderLine] = []

    def to_xml(self) -> etree._Element:
        elem = etree.Element(_tag("Document.ЗаказКлиента"))
        _sub(elem, "Ref_Key", self.ref_key)
        _sub(elem, "Number", self.number)
        _sub(elem, "Date", self.date)
        _sub(elem, "СтатусЗаказа", self.status)
        _sub(elem, "КонтрагентRef_Key", self.counterparty_key)
        _sub(elem, "СкладRef_Key", self.warehouse_key)
        _sub(elem, "Комментарий", self.comment)
        rows = etree.SubElement(elem, _tag("Товары"))
        for line in self.lines:
            row = etree.SubElement(rows, _tag("Row"))
            _sub(row, "НомерСтроки", str(line.line_number))
            _sub(row, "НоменклатураRef_Key", line.nomenclature_key)
            _sub(row, "Количество", str(line.quantity))
            _sub(row, "Цена", str(line.price))
            _sub(row, "Сумма", str(line.amount))
            _sub(row, "СуммаНДС", str(line.vat_amount))
        return elem

    @classmethod
    def from_xml(cls, elem: etree._Element) -> EDSalesOrder:
        lines: list[EDSalesOrderLine] = []
        rows_elem = elem.find(_tag("Товары"))
        if rows_elem is not None:
            for row in rows_elem.findall(_tag("Row")):
                lines.append(
                    EDSalesOrderLine(
                        line_number=int(_text(row, "НомерСтроки") or "0"),
                        nomenclature_key=_text(row, "НоменклатураRef_Key"),
                        quantity=Decimal(_text(row, "Количество") or "0"),
                        price=Decimal(_text(row, "Цена") or "0"),
                        amount=Decimal(_text(row, "Сумма") or "0"),
                        vat_amount=Decimal(_text(row, "СуммаНДС") or "0"),
                    )
                )
        return cls(
            ref_key=_text(elem, "Ref_Key"),
            number=_text(elem, "Number"),
            date=_text(elem, "Date"),
            status=_text(elem, "СтатусЗаказа") or "НеСогласован",
            counterparty_key=_text(elem, "КонтрагентRef_Key"),
            warehouse_key=_text(elem, "СкладRef_Key"),
            comment=_text(elem, "Комментарий"),
            lines=lines,
        )


class EDNomenclaturePrice(BaseModel):
    """ЦенаНоменклатуры (InformationRegister.ЦеныНоменклатуры)."""

    nomenclature_key: str
    price_type_key: str
    price: Decimal
    currency: str = "RUB"
    period: str = ""

    def to_xml(self) -> etree._Element:
        elem = etree.Element(_tag("InformationRegister.ЦеныНоменклатуры"))
        _sub(elem, "НоменклатураRef_Key", self.nomenclature_key)
        _sub(elem, "ВидЦеныRef_Key", self.price_type_key)
        _sub(elem, "Цена", str(self.price))
        _sub(elem, "Валюта", self.currency)
        _sub(elem, "Период", self.period)
        return elem

    @classmethod
    def from_xml(cls, elem: etree._Element) -> EDNomenclaturePrice:
        return cls(
            nomenclature_key=_text(elem, "НоменклатураRef_Key"),
            price_type_key=_text(elem, "ВидЦеныRef_Key"),
            price=Decimal(_text(elem, "Цена") or "0"),
            currency=_text(elem, "Валюта") or "RUB",
            period=_text(elem, "Период"),
        )


class EDNomenclatureStock(BaseModel):
    """ОстатокНоменклатуры (AccumulationRegister.ТоварыНаСкладах)."""

    nomenclature_key: str
    warehouse_key: str
    quantity: Decimal
    reserved: Decimal = Decimal("0")

    def to_xml(self) -> etree._Element:
        elem = etree.Element(_tag("AccumulationRegister.ТоварыНаСкладах"))
        _sub(elem, "НоменклатураRef_Key", self.nomenclature_key)
        _sub(elem, "СкладRef_Key", self.warehouse_key)
        _sub(elem, "КоличествоОстаток", str(self.quantity))
        _sub(elem, "КоличествоРезерв", str(self.reserved))
        return elem

    @classmethod
    def from_xml(cls, elem: etree._Element) -> EDNomenclatureStock:
        return cls(
            nomenclature_key=_text(elem, "НоменклатураRef_Key"),
            warehouse_key=_text(elem, "СкладRef_Key"),
            quantity=Decimal(_text(elem, "КоличествоОстаток") or "0"),
            reserved=Decimal(_text(elem, "КоличествоРезерв") or "0"),
        )


# Соответствие XML-тегов и классов схем
ED_ENTITY_CLASSES: dict[str, type[Any]] = {
    "Catalog.Номенклатура": EDNomenclature,
    "Catalog.Контрагенты": EDCounterparty,
    "Catalog.Склады": EDWarehouse,
    "Document.ЗаказКлиента": EDSalesOrder,
    "InformationRegister.ЦеныНоменклатуры": EDNomenclaturePrice,
    "AccumulationRegister.ТоварыНаСкладах": EDNomenclatureStock,
}
