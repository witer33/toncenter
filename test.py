from src.toncenter.client import Client
import asyncio


async def main():

    async with Client(open("main_api_token.txt").read()) as client:
        for _ in range(30):
            info = await client.get_masterchain_info()
            print(info.last)


if __name__ == "__main__":
    asyncio.run(main())
