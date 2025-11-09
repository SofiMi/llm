import asyncio
from bot.bot import start as bot_start

async def main():
    await bot_start()

if __name__ == "__main__":
    asyncio.run(main())