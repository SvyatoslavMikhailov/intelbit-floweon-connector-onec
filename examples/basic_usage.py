"""Пример: подключение OneCConnector и чтение каталога.

v0.0.1 — skeleton. Методы поднимают NotImplementedError.
Реальный пример появится в v0.1.0.
"""

import asyncio

from intelbit_river_connector_onec import OneCConnector


async def main() -> None:
    connector = OneCConnector(
        config={
            "base_url": "http://1c-server.example.com/UT11",
            "auth_type": "basic",
            "username": "river_user",
            "password": "secret",
        }
    )

    # v0.0.1: вызов поднимет NotImplementedError
    # items = await connector.read_catalog("Номенклатура")
    print(f"Connector config: {connector.config['base_url']}")
    print("OneCConnector skeleton ready. Implementation in v0.1.0.")


if __name__ == "__main__":
    asyncio.run(main())
