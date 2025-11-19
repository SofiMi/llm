from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram import F

from bot.db import register_user_simple, user_exists
from bot.states import RegistrationStates
from bot.dispatcher import dp

@dp.message(Command("start"), F.chat.type == "private")
async def command_start_handler(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    
    if not await user_exists(tg_id):
        await register_user_simple(tg_id)
        await message.answer(
            "🎉 Добро пожаловать! Вы успешно зарегистрированы.\n\n"
            "🤖 Этот бот умеет:\n"
            "• Помогать вам вести диалог с помощью AI\n"
            "• Поддерживать диалог в режиме сессии\n\n"
            "💡 Для начала общения с AI просто напишите мне любое сообщение или используйте команду /session"
        )
    else:
        await message.answer(
            "С возвращением! 🤖\n\n"
            "Вы можете:\n"
            "• Начать сессию с AI командой /session\n"
            "• Просто написать сообщение AI\n"
            "• Завершить сессию командой /stop"
        )
    
    await state.set_state(RegistrationStates.waiting_for_llm_session)