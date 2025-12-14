import aiohttp
from langchain_core.documents import Document
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from urllib.parse import urlparse
import asyncio


class SiteParser:
    def __init__(self, user_agent: str = "Mozilla/5.0"):
        self.user_agent = user_agent

    async def fetch_html(self, url: str) -> Optional[str]:
        headers = {"User-Agent": self.user_agent}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.text()
            except Exception as ex:
                print(f"Ошибка скачивания {url}: {ex}")
                return None

    def _html_to_document(self, html: str, url: str, parse_classes: List[str] = None) -> Optional[Document]:
        soup = BeautifulSoup(html, "lxml")
        if parse_classes:
            content = "\n".join(
                tag.get_text(separator=" ", strip=True)
                for c in parse_classes
                for tag in soup.find_all(class_=c)
            )
        else:
            content = soup.get_text(separator=" ", strip=True)
        if not content.strip():
            return None
        return Document(
            page_content=content,
            metadata={"source": url, "parsed_classes": parse_classes or []}
        )

    async def fetch_site(self, url: str, parse_classes: List[str] = None) -> Optional[Document]:
        html = await self.fetch_html(url)
        if html:
            return self._html_to_document(html, url, parse_classes=parse_classes)
        return None

    async def fetch_sites(self, urls: List[str], parse_classes: List[str] = None) -> List[Document]:
        tasks = [self.fetch_site(url, parse_classes=parse_classes) for url in urls]
        docs = await asyncio.gather(*tasks)
        return [doc for doc in docs if doc is not None]


if __name__ == "__main__":
    async def main():
        parser = SiteParser()
        urls = [
            "https://ru.wikipedia.org/wiki/Тест",
            "https://lilianweng.github.io/posts/2023-06-23-agent/"
        ]
        docs = await parser.fetch_sites(urls, parse_classes=["post-content", "post-header"])
        for doc in docs:
            print("---", doc.metadata)
            print(doc.page_content[:800])

    asyncio.run(main())
