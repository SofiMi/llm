import asyncpg
from bot.config import DATABASE_URL
from bot.db_pool import get_pool

async def register_user_simple(tg_id: int):
    """Регистрация пользователя по ID"""
    pool = await get_pool()
    async with pool.acquire() as connection:
        if not await user_exists(tg_id):
            await connection.execute('''
                INSERT INTO "User" (tg_id) VALUES ($1)
            ''', tg_id)

async def user_exists(tg_id: int) -> bool:
    """Проверка существования пользователя"""
    pool = await get_pool()
    async with pool.acquire() as connection:
        user = await connection.fetchrow(
            'SELECT 1 FROM "User" WHERE tg_id = $1', tg_id
        )
        return user is not None

async def get_user_id(tg_id: int) -> int:
    """Получение ID пользователя из БД"""
    pool = await get_pool()
    async with pool.acquire() as connection:
        user = await connection.fetchrow(
            'SELECT id FROM "User" WHERE tg_id = $1', tg_id
        )
        return user['id'] if user else None