# toncenter
Toncenter API Python3 async wrap.

# Example

```python
from toncenter.client import Client
import asyncio


async def main():
    
    async with Client(open("main_api_token.txt").read()) as client:
        info = await client.get_masterchain_info() # Gets masterchain info
        print(info.last) # Prints last block


if __name__ == "__main__":
    asyncio.run(main())
```
