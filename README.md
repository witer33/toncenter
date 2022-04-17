# toncenter
Toncenter API Python3 async wrap.

# Installation

```sh
pip3 install toncenter
```

# Documentation (WIP)

https://witer33.github.io/toncenter/

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
# Example without context manager

```python
from toncenter.client import Client
import asyncio


async def main():
    
    client = Client(open("main_api_token.txt").read())
    await client.start()
    
    info = await client.get_masterchain_info() # Gets masterchain info
    print(info.last) # Prints last block
    
    await client.stop() # ALWAYS call this method.


if __name__ == "__main__":
    asyncio.run(main())
```
