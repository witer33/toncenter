from typing import Tuple, Optional, List, Callable, Coroutine, Hashable, Any
from .client import BlockID, Client, BlockHeader, STANDARD_SHARD
import asyncio
import time
from abc import ABC, abstractmethod
import aiosqlite
import traceback


class TemporaryMap:
    """
    Map with expiration time.
    """

    def __init__(self):
        self._map = {}

    def set_item(self, key: Hashable, value: Any, expire_in: int = -1) -> None:
        self._map[key] = (value, int(time.time()) + expire_in if expire_in > 0 else -1)

    def __getitem__(self, key: Hashable) -> Any:
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
        self.cleaner_task = asyncio.create_task(self.cleaner())
    
    async def stop(self) -> None:
        self.cleaner_task.cancel()


class TxStorage(ABC):
    """
    Storage for transactions.
    """

    @abstractmethod
    async def get_txs(self, address: str) -> List[Tuple[int, str]]:
        pass

    @abstractmethod
    async def add_tx(self, address: str, amount: int, message: Optional[str] = "", expire_in: Optional[int] = -1) -> None:
        pass

    @abstractmethod
    async def get_last_seqno(self) -> int:
        pass

    @abstractmethod
    async def set_last_seqno(self, seqno: int) -> None:
        pass


class SqliteStorage(TxStorage):

    def __init__(self, db_file: str = "ton.db") -> None:
        super().__init__()
        self.db_file = db_file
        self.started = False
        self.db = None
    
    async def start(self, delay: int = 60) -> None:
        if self.started:
            return
        self.db = await aiosqlite.connect(self.db_file)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                address TEXT NOT NULL PRIMARY KEY,
                amount INTEGER, 
                message TEXT, 
                expire_in INTEGER
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS expire_in_index ON transactions (expire_in)
        """)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS storage (
                key TEXT NOT NULL PRIMARY KEY,
                value TEXT
            )
        """)
        await self.db.commit()
        asyncio.create_task(self.start_cleanup(delay))
        self.started = True
    
    async def stop(self) -> None:
        await self.db.close()

    async def __aenter__(self) -> 'SqliteStorage':
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def add_tx(self, address: str, amount: int, message: Optional[str] = "", expire_in: Optional[int] = -1) -> None:
        await self.db.execute("""
            INSERT INTO transactions (address, amount, message, expire_in)
            VALUES (?, ?, ?, ?)
        """, (address, amount, message, expire_in))
        await self.db.commit()
    
    async def get_txs(self, address: str) -> List[Tuple[int, str]]:
        await self.db.execute("""
            SELECT amount, message FROM transactions WHERE address = ?
        """, (address,))
        return [(amount, message) for amount, message in await self.db.fetchall()]
    
    async def cleanup(self) -> None:
        await self.db.execute("""
            DELETE FROM transactions WHERE expire_in != -1 AND expire_in < ?
        """, (int(time.time()),))
        await self.db.commit()
    
    async def start_cleanup(self, delay: int) -> None:
        while True:
            await asyncio.sleep(delay)
            await self.cleanup()
        
    async def set(self, key: str, value: str) -> None:
        await self.db.execute("""
            INSERT OR REPLACE INTO storage (key, value) VALUES (?, ?)
        """, (key, value))
        await self.db.commit()
    
    async def get(self, key: str) -> str:
        async with self.db.execute("SELECT value FROM storage WHERE key = ?", (key,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return result[0]
            return ""
        
    async def set_last_seqno(self, seqno: int) -> None:
        await self.set("last_seqno", str(seqno))
    
    async def get_last_seqno(self) -> int:
        seqno = await self.get("last_seqno")
        if seqno != "":
            return int(seqno)
        return 0


class BlockHandler:
    """
    Calls any number of used defined handlers for each block.
    """

    def __init__(self, client: Client, last_seqno: int = -1, delay: float = 1, on_checked_seqno: Callable = None) -> None:
        self.handlers: List[Callable[[BlockID], Coroutine]] = []
        self.client = client
        self.delay = delay
        if last_seqno >= 0:
            self.last_checked_seqno = last_seqno
        else:
            self.last_checked_seqno = None
        self.on_checked_seqno = on_checked_seqno
    
    def add_handler(self, handler: Callable[[BlockID], Coroutine]) -> None:
        self.handlers.append(handler)
    
    async def call_handlers(self, block_id: BlockID) -> None:
        for handler in self.handlers:
            try:
                await handler(block_id)
            except Exception as e:
                print(f"Error in handler: {e}")
                traceback.print_exc()
    
    async def block_checker(self) -> None:
        while True:
            await asyncio.sleep(self.delay)
            try:
                last_seqno = (await self.client.get_masterchain_info()).last.seqno
                for seqno in range(self.last_checked_seqno + 1, last_seqno + 1):
                    asyncio.create_task(self.call_handlers(BlockID(workchain=-1, shard=STANDARD_SHARD, seqno=seqno)))
                    shards = await self.client.get_shards(seqno)
                    for block_id in shards.shards:
                        asyncio.create_task(self.call_handlers(block_id))
                    self.last_checked_seqno = seqno
                    if self.on_checked_seqno:
                        await self.on_checked_seqno(seqno)
            except:
                print("Caught an error while checking blocks")
                traceback.print_exc()

    async def start(self) -> None:
        if self.last_checked_seqno is None:
            self.last_checked_seqno = (await self.client.get_masterchain_info()).last.seqno
        self.checker = asyncio.create_task(self.block_checker())
    
    async def stop(self) -> None:
        self.checker.cancel()
    
    async def __aenter__(self) -> 'BlockHandler':
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

class Ticker:
    """
    WIP NOT WORKING.

    Calls a user defined handler when a registered transaction is found.
    """

    def __init__(self, client: Client, storage: TxStorage, delay: float = 1) -> None:
        self.block_handler = BlockHandler(client=client, delay=delay)
        self.block_handler.add_handler(self.block_receiver)
        self.storage = storage
        self.client = client
        self.handler: Callable[[str, int, str], Coroutine] = None
    
    async def start(self) -> None:
        await self.storage.start()
        await self.block_handler.start()
    
    async def stop(self) -> None:
        await self.block_handler.stop()
    
    async def __aenter__(self) -> 'Ticker':
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
    
    async def block_receiver(self, block_id: BlockID) -> None:
        txs = await self.client.get_block_transactions(block_id)
    
    async def set_handler(self, handler: Callable[[str, int, str], Coroutine]) -> None:
        self.handler = handler