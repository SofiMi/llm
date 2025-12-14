from aiogram.types import BotCommand
from bot.bot_instance import get_bot

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Регистрация/информация"),
        BotCommand(command="session", description="Начать сессию с AI"),
        BotCommand(command="stop", description="Завершить сессию с AI"),
        BotCommand(command="add_channel", description="Добавить Telegram канал для анализа"),
        BotCommand(command="stats", description="Статистика RAG базы данных"),
    ]
    bot = get_bot()
    await bot.set_my_commands(commands)
