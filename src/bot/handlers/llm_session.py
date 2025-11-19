from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram import F

from bot.states import LLMSessionStates, RegistrationStates
from bot.dispatcher import dp
from bot.db import user_exists

# Заглушка
async def call_llm(user_message: str, user_id: int) -> str:
    # Реализовать вызов LLM API
    return f"🤖 Ответ AI (заглушка):\n\nВы написали: '{user_message}'\n\nЭтот функционал будет реализован позже!"

@dp.message(Command("session"))
async def start_llm_session(message: types.Message, state: FSMContext):
    if not await user_exists(message.from_user.id):
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    await state.set_state(LLMSessionStates.active_session)
    await message.answer(
        "💫 Сессия с AI начата!\n\n"
        "Теперь все ваши сообщения будут обрабатываться AI. "
        "Для выхода из сессии используйте /stop\n\n"
        "Задавайте ваш вопрос:"
    )

@dp.message(Command("stop"))
async def stop_llm_session(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == LLMSessionStates.active_session:
        await state.set_state(RegistrationStates.waiting_for_llm_session)
        await message.answer(
            "🛑 Сессия с AI завершена.\n\n"
            "Чтобы начать новую сессию, используйте /session или просто напишите сообщение"
        )
    else:
        await message.answer("❌ Вы не в активной сессии с AI")

@dp.message(LLMSessionStates.active_session)
async def handle_llm_message(message: types.Message, state: FSMContext):
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    # Заглушка
    response = await call_llm(message.text, message.from_user.id)
    
    await message.answer(response)

@dp.message(RegistrationStates.waiting_for_llm_session)
async def handle_regular_message(message: types.Message, state: FSMContext):
    if not await user_exists(message.from_user.id):
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🎯 Начать сессию с AI", callback_data="start_session")
            ]
        ]
    )
    
    await message.answer(
        "💡 Вы можете начать сессию с AI для полноценного диалога!\n\n"
        "В режиме сессии AI будет помнить контекст разговора. "
        "Используйте кнопку ниже или команду /session",
        reply_markup=markup
    )

@dp.callback_query(F.data == "start_session")
async def process_start_session(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(LLMSessionStates.active_session)
    await callback.message.edit_text(
        "💫 Сессия с AI начата!\n\n"
        "Теперь все ваши сообщения будут обрабатываться AI. "
        "Для выхода из сессии используйте /stop\n\n"
        "Задавайте ваш вопрос:"
    )
    await callback.answer()