from src.toncenter.client import Client, BlockID, BlockHeader
from src.toncenter.ticker import SqliteStorage, BlockHandler, Ticker
import asyncio


async def main():

    async with Client(open("test_api_token.txt").read(), base_url="https://testnet.toncenter.com/api/v2/") as client:
        storage = SqliteStorage("test.db")
        await storage.start()
        async with Ticker(client, storage, delay=0.5) as ticker:
            await asyncio.sleep(100)


if __name__ == "__main__":
    asyncio.run(main())
