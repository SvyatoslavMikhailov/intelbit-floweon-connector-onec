"""EnterpriseData XML-клиент для обмена данными с 1С (схема v1.5, УТ 11.5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from lxml import etree
from pydantic import BaseModel, Field

from intelbit_floweon_connector_onec.auth import OneCAuth
from intelbit_floweon_connector_onec.enterprise_data_schema import (
    ED_ENTITY_CLASSES,
    NS,
    _tag,
)

# XXE-защита: внешние/внутренние сущности не раскрываются, сеть парсеру запрещена.
_PARSER = etree.XMLParser(encoding="utf-8", recover=False, resolve_entities=False, no_network=True)


class EnterpriseDataMessage(BaseModel):
    """Сообщение EnterpriseData — конверт для набора сущностей."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    entities: list[dict[str, Any]] = Field(default_factory=list)


class EnterpriseDataClient:
    """Клиент протокола EnterpriseData 1.5 (XML-обмен через HTTP)."""

    def __init__(self, config: dict[str, Any], auth: OneCAuth) -> None:
        self._base_url = config["base_url"].rstrip("/")
        self._plan: str = config.get("plan", "ОсновнойПланОбмена")
        self._node: str = config.get("node", "ЦентральныйУзел")
        self._schema_version: str = config.get("schema_version", "1.5")
        self._auth = auth

    async def send_message(self, entities: list[dict[str, Any]]) -> str:
        """Отправить XML-сообщение в 1С. Возвращает message_id."""
        message_id = str(uuid.uuid4())
        xml_bytes = self._build_xml(message_id, entities)
        headers = await self._auth.get_headers()
        headers["Content-Type"] = "application/xml; charset=utf-8"
        url = f"{self._base_url}/exchange/{self._plan}/{self._node}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, content=xml_bytes, headers=headers, timeout=30.0)
            response.raise_for_status()
        return message_id

    async def receive_messages(
        self, plan: str | None = None, node: str | None = None
    ) -> list[EnterpriseDataMessage]:
        """Получить XML-сообщения из 1С, вернуть распарсенные объекты."""
        plan = plan or self._plan
        node = node or self._node
        headers = await self._auth.get_headers()
        url = f"{self._base_url}/exchange/{plan}/{node}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
        return self._parse_xml(response.content)

    def _build_xml(self, message_id: str, entities: list[dict[str, Any]]) -> bytes:
        nsmap: dict[str | None, str] = {None: NS}
        root = etree.Element(_tag("Message"), nsmap=nsmap)  # type: ignore[arg-type]
        header = etree.SubElement(root, _tag("Header"))
        etree.SubElement(header, _tag("MessageId")).text = message_id
        etree.SubElement(header, _tag("CreatedAt")).text = datetime.now(UTC).isoformat(
            timespec="seconds"
        )
        etree.SubElement(header, _tag("SourceNode")).text = self._node
        body = etree.SubElement(root, _tag("Body"))
        for entity in entities:
            entity_tag = entity.get("__type__", "Catalog.Номенклатура")
            elem = etree.SubElement(body, _tag(entity_tag))
            for key, value in entity.items():
                if key != "__type__":
                    etree.SubElement(elem, _tag(key)).text = str(value)
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    def _parse_xml(self, content: bytes) -> list[EnterpriseDataMessage]:
        root = etree.fromstring(content, _PARSER)
        header_elem = root.find(_tag("Header"))
        message_id = ""
        created_at = datetime.now(UTC)
        if header_elem is not None:
            mid = header_elem.find(_tag("MessageId"))
            if mid is not None and mid.text:
                message_id = mid.text
            cat = header_elem.find(_tag("CreatedAt"))
            if cat is not None and cat.text:
                from dateutil.parser import parse as parse_dt

                created_at = parse_dt(cat.text)

        entities: list[dict[str, Any]] = []
        body_elem = root.find(_tag("Body"))
        if body_elem is not None:
            for child in body_elem:
                local_tag = etree.QName(child.tag).localname
                schema_cls = ED_ENTITY_CLASSES.get(local_tag)
                if schema_cls is not None and hasattr(schema_cls, "from_xml"):
                    obj = schema_cls.from_xml(child)
                    d: dict[str, Any] = obj.model_dump()
                    d["__type__"] = local_tag
                    entities.append(d)
                else:
                    raw: dict[str, Any] = {"__type__": local_tag}
                    for sub in child:
                        raw[etree.QName(sub.tag).localname] = sub.text or ""
                    entities.append(raw)

        return [
            EnterpriseDataMessage(
                message_id=message_id,
                created_at=created_at,
                entities=entities,
            )
        ]
