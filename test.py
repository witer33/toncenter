from toncenter.client import Client
import time
import asyncio


client = Client(base_url="https://testnet.toncenter.com/api/v2/")

async def main():

    await client.start()

    print((await client.get_masterchain_info()).last)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
