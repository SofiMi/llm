from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram import F
import json

from bot.states import LLMSessionStates, RegistrationStates
from bot.dispatcher import dp
from bot.db import user_exists
from bot.session_context import SessionContextManager
from rag_integration import parse_telegram_channel, query_rag_system, get_rag_stats

manager = SessionContextManager()

async def get_session_context(state: FSMContext) -> SessionContextManager:
    return manager

async def save_session_context(state: FSMContext, context_manager: SessionContextManager):
    """Сохранить менеджер контекста в состояние"""
    await state.update_data(session_context=context_manager.to_dict())

async def call_llm(user_message: str, user_id: int, dialog_context: str = "") -> str:
    """Вызов RAG системы для ответа на вопросы пользователя с учетом контекста"""
    return await query_rag_system(user_message, user_id, dialog_context)

async def start_llm_session(message: types.Message, state: FSMContext):
    if not await user_exists(message.from_user.id):
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return

    current_state = await state.get_state()

    if current_state == LLMSessionStates.active_session:
        context_manager = await get_session_context(state)
        stats = context_manager.get_session_stats()

        await message.answer(
            f"💫 Вы уже в активной сессии с AI!\n\n"
            f"📊 В текущем диалоге: {stats['user_messages']} вопросов и {stats['assistant_messages']} ответов\n\n"
            "Продолжайте диалог или используйте /stop для завершения сессии."
        )
        return

    context_manager = SessionContextManager()
    await save_session_context(state, context_manager)

    await state.set_state(LLMSessionStates.active_session)
    await message.answer(
        "💫 Новая сессия с AI начата!\n\n"
        "Теперь все ваши сообщения будут обрабатываться AI с сохранением контекста диалога. "
        "Для выхода из сессии используйте /stop\n\n"
        "Задавайте ваш вопрос:"
    )

async def stop_llm_session(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == LLMSessionStates.active_session:
        context_manager = await get_session_context(state)
        session_stats = context_manager.get_session_stats()

        context_manager.clear_session()
        await save_session_context(state, context_manager)

        await state.set_state(RegistrationStates.waiting_for_llm_session)

        stats_text = ""
        if session_stats["total_messages"] > 0:
            stats_text = f"\n📊 В диалоге было {session_stats['user_messages']} вопросов и {session_stats['assistant_messages']} ответов"

        await message.answer(
            f"🛑 Сессия с AI завершена.{stats_text}\n\n"
            "Чтобы начать новую сессию, используйте /session или просто напишите сообщение"
        )
    else:
        await message.answer("❌ Вы не в активной сессии с AI")

async def handle_llm_message(message: types.Message, state: FSMContext):
    await message.bot.send_chat_action(message.chat.id, "typing")

    context_manager = await get_session_context(state)
    context_manager.add_message("user", message.text, message.message_id)
    dialog_context = context_manager.get_context_for_llm()
    response = await call_llm(message.text, message.from_user.id, dialog_context)
    context_manager.add_message("assistant", response)
    await save_session_context(state, context_manager)

    await message.answer(response)

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

async def process_start_session(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state == LLMSessionStates.active_session:
        context_manager = await get_session_context(state)
        stats = context_manager.get_session_stats()

        await callback.message.edit_text(
            f"💫 Вы уже в активной сессии с AI!\n\n"
            f"📊 В текущем диалоге: {stats['user_messages']} вопросов и {stats['assistant_messages']} ответов\n\n"
            "Продолжайте диалог или используйте /stop для завершения сессии."
        )
        await callback.answer()
        return

    context_manager = SessionContextManager()
    await save_session_context(state, context_manager)

    await state.set_state(LLMSessionStates.active_session)
    await callback.message.edit_text(
        "💫 Новая сессия с AI начата!\n\n"
        "Теперь все ваши сообщения будут обрабатываться AI с сохранением контекста диалога. "
        "Для выхода из сессии используйте /stop\n\n"
        "Задавайте ваш вопрос:"
    )
    await callback.answer()

async def add_telegram_channel(message: types.Message):
    print("add_channel")
    """Команда для добавления Telegram канала в RAG систему"""
    if not await user_exists(message.from_user.id):
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return

    args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    if not args:
        await message.answer(
            "📋 Использование: /add_channel <ссылка на канал>\n\n"
            "Примеры:\n"
            "• /add_channel https://t.me/channel_name\n"
            "⚡ Будет загружено до 30 последних постов из канала"
        )
        return

    channel_link = args[0]
    limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 30

    await message.answer("🔄 Загружаю посты из канала... Это может занять некоторое время.")
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        print(f"[DEBUG] Парсинг канала: {channel_link}, лимит: {limit}")
        result = await parse_telegram_channel(channel_link, limit)
        print(f"[DEBUG] Результат: {result}")
        await message.answer(result)

        stats = get_rag_stats()
        print(f"[DEBUG] Статистика после добавления: {stats}")
        # await message.answer(f"📊 Проверка: {stats}")

    except Exception as e:
        error_msg = f"❌ Ошибка при загрузке канала: {str(e)}"
        print(f"[DEBUG] Ошибка: {error_msg}")
        await message.answer(error_msg)

async def show_rag_stats(message: types.Message):
    """Команда для просмотра статистики RAG системы"""
    if not await user_exists(message.from_user.id):
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return

    stats = get_rag_stats()
    await message.answer(stats)
