import asyncpg
from bot.config import DATABASE_URL

db_pool = None

async def create_db_pool():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    return db_pool

async def get_pool():
    return db_pool 