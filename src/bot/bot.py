import asyncio
from bot.db_pool import create_db_pool
from bot.dispatcher import dp, get_dispatcher
from bot.bot_instance import get_bot
from bot.command_menu import set_bot_commands

from bot.handlers.registration import command_start_handler
from bot.handlers.llm_session import (
    handle_llm_message, 
    handle_regular_message,
    start_llm_session,
    stop_llm_session,
    process_start_session
)

from bot.states import RegistrationStates, LLMSessionStates
from aiogram.filters import Command
from aiogram import F

async def on_startup():
    await set_bot_commands()

async def start():
    await create_db_pool()
    
    dp = get_dispatcher()
    
    dp.message.register(command_start_handler, Command("start"), F.chat.type == "private")
    dp.message.register(start_llm_session, Command("session"))
    dp.message.register(stop_llm_session, Command("stop"))
    
    dp.message.register(handle_llm_message, LLMSessionStates.active_session)
    dp.message.register(handle_regular_message, RegistrationStates.waiting_for_llm_session)
    
    dp.callback_query.register(process_start_session, F.data == "start_session")

    dp.startup.register(on_startup)
    bot = get_bot()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start())