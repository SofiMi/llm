from bot.db_pool import registered_users

async def register_user_simple(tg_id: int):
    """Регистрация пользователя по ID"""
    if not await user_exists(tg_id):
        registered_users.add(tg_id)
        print(f"👤 Пользователь {tg_id} зарегистрирован в памяти")

async def user_exists(tg_id: int) -> bool:
    """Проверка существования пользователя"""
    return tg_id in registered_users

async def get_user_id(tg_id: int) -> int:
    """Получение ID пользователя (упрощенно - просто tg_id)"""
    if await user_exists(tg_id):
        return tg_id
    return None
