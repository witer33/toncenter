from src.toncenter.client import Client, Transaction
from src.toncenter.payment import PaymentReceiver
import asyncio

async def main():

    async with Client(open("test_api_token.txt").read(), base_url="https://testnet.toncenter.com/api/v2/") as client:
        async with PaymentReceiver(client, "EQBUdV7ebJT1bdR-6NggOa1YO0n7gScKZrHAAY3jX5oO515t", delay=0.5) as receiver:
            async def handler(tx: Transaction):
                print(tx.in_msg.message)
            receiver.set_handler(handler)
            await asyncio.sleep(1000)


if __name__ == "__main__":
    asyncio.run(main())
