import os
from typing import List, Optional
from langchain_core.documents import Document
from telethon import TelegramClient
from dotenv import load_dotenv
from contextlib import asynccontextmanager


load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")


class TelegramPostsParser:
    def __init__(self, api_id: str = API_ID, api_hash: str = API_HASH, session: str = "telegram-crawler"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session = session

    @asynccontextmanager
    async def client(self):
        client = TelegramClient(self.session, self.api_id, self.api_hash)
        await client.start()
        try:
            yield client
        finally:
            await client.disconnect()

    def _msg_document(self, message, channel_link) -> Optional[Document]:
        txt = message.text or message.message or ""
        if not txt:
            return None
        return Document(
            page_content=txt,
            metadata={
                "source": channel_link,
                "date": str(message.date),
                "post_id": message.id,
            }
        )

    async def fetch_channel_posts(self, channel_link, limit=30) -> List[Document]:
        docs = []
        async with self.client() as client:
            try:
                channel = await client.get_entity(channel_link)
                messages = await client.get_messages(channel, limit=limit)
                for m in messages:
                    doc = self._msg_document(m, channel_link=channel_link)
                    if doc:
                        docs.append(doc)
            except Exception as ex:
                print(f"Ошибка загрузки постов для {channel_link}: {ex}")
        return docs

if __name__ == "__main__":
    async def _test():
        parser = TelegramPostsParser()
        docs = await parser.fetch_channel_posts(DEFAULT_CHANNEL, 5)
    asyncio.run(_test())
