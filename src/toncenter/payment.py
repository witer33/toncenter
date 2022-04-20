from .client import Client, Transaction
from typing import Coroutine, Callable
import asyncio
import traceback


class PaymentReceiver:
    """
    Calls an handler whenever a payment to a specific address is received.
    """

    def __init__(self, client: Client, address: str, delay: int = 1, result_limit: int = 30) -> None:
        self.client = client
        self.address = address
        self.delay = delay
        self.result_limit = result_limit
        self.handler = None
        self.checker_task = None
        self.last_lt = 0
    
    def set_handler(self, handler: Callable[[Transaction], Coroutine]) -> None:
        self.handler = handler
    
    async def check_payment(self) -> None:
        transactions = await self.client.get_transactions(self.address, limit=self.result_limit)
        for tx in transactions:
            if int(tx.transaction_id.lt) <= self.last_lt:
                continue
            if self.handler and tx.in_msg and len(tx.out_msgs) == 0 and tx.in_msg.source != "" and tx.in_msg.destination == self.address:
                asyncio.create_task(self.handler(tx))
        self.last_lt = max([int(tx.transaction_id.lt) for tx in transactions]) if len(transactions) > 0 else self.last_lt
    
    async def start_check(self) -> None:
        while True:
            await asyncio.sleep(self.delay)
            try:
                await self.check_payment()
            except:
                traceback.print_exc()
    
    async def start(self) -> None:
        self.checker_task = asyncio.create_task(self.start_check())
    
    async def stop(self) -> None:
        self.checker_task.cancel()
    
    async def __aenter__(self) -> 'PaymentReceiver':
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()