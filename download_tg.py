import os
import asyncio
import logging
from typing import List, Optional
from langchain_core.documents import Document
from telethon import TelegramClient
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramPostsParser:
    def __init__(self, api_id: str = API_ID, api_hash: str = API_HASH, session: str = "telegram-crawler"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session = session
        self.max_text_length = 100000

    @asynccontextmanager
    async def client(self):
        """Простое создание и управление клиентом Telegram"""
        client = TelegramClient(self.session, self.api_id, self.api_hash)
        try:
            await client.start()
            yield client
        finally:
            await client.disconnect()

    def _msg_document(self, message, channel_link) -> Optional[Document]:
        """Создание документа из сообщения"""
        try:
            txt = message.text or message.message or ""

            if hasattr(message, 'caption') and message.caption:
                txt = txt + " " + message.caption if txt else message.caption

            if not txt or len(txt.strip()) < 10:
                return None

            if len(txt) > self.max_text_length:
                txt = txt[:self.max_text_length] + "... [обрезано]"

            return Document(
                page_content=txt.strip(),
                metadata={
                    "source": channel_link,
                    "date": str(message.date),
                    "post_id": message.id,
                    "text_length": len(txt),
                    "has_media": bool(message.media)
                }
            )
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения {getattr(message, 'id', 'unknown')}: {e}")
            return None

    async def fetch_channel_posts(self, channel_link: str, limit: int = 30) -> List[Document]:
        """Простая загрузка постов из канала"""
        docs = []

        try:
            logger.info(f"Парсинг канала: {channel_link}, лимит: {limit}")

            async with self.client() as client:
                channel = await client.get_entity(channel_link)
                logger.info(f"Канал найден: {getattr(channel, 'title', 'неизвестный')}")

                messages = await client.get_messages(channel, limit=limit)

                if not messages:
                    logger.warning("Сообщений не найдено")
                    return []

                logger.info(f"Получено {len(messages)} сообщений, обработка...")

                for i, message in enumerate(messages, 1):
                    doc = self._msg_document(message, channel_link)
                    print(message, doc)
                    if doc:
                        docs.append(doc)
                        logger.debug(f"Обработано сообщение {i}/{len(messages)}")

                logger.info(f"Обработка завершена: {len(docs)} документов из {len(messages)} сообщений")

        except Exception as e:
            logger.error(f"Ошибка загрузки постов для {channel_link}: {e}")
            raise Exception(f"Ошибка парсинга канала {channel_link}: {str(e)}")

        return docs
