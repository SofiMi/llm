from aiogram import Bot
from bot.config import TOKEN

bot = Bot(TOKEN)

def get_bot():
    return bot 