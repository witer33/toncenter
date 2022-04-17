from toncenter.client import Client
import asyncio
import time


class TemporaryMap:
    def __init__(self):
        self._map = {}

    def set_item(self, key: str, value: str, expire_in: int = -1) -> None:
        self._map[key] = (value, int(time.time()) + expire_in if expire_in > 0 else -1)

    def __getitem__(self, key: str) -> str:
        if key in self._map:
            value, expire_in = self._map[key]
            if expire_in > 0 and expire_in < int(time.time()):
                del self._map[key]
                return None
            return value
        return None

    async def cleaner(self) -> None:
        while True:
            await asyncio.sleep(self.delay)
            for key in self._map.keys():
                _, expire_in = self._map[key]
                if expire_in > 0 and expire_in < int(time.time()):
                    del self._map[key]

    async def start(self, delay: int = 10) -> None:
        self.delay = delay
        asyncio.create_task(self.cleaner())


class Ticker:
    """
    WIP (not working)
    """

    def __init__(self, client: Client, delay: float = 0.1) -> None:
        self.client = client
        self.delay = delay
        self.waiting_txs = TemporaryMap()

    async def start(self) -> None:
        await self.waiting_txs.start()

    async def checker(self) -> None:
        while True:
            await asyncio.sleep(self.delay)

    def add_tx(self, address: str, amount: int, uid: str, expire_in: int = 300) -> None:
        self.waiting_txs.set_item(uid, (address, amount), expire_in)
