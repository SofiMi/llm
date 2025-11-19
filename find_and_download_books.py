import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


TARGET_FORMATS = ('.txt', '.pdf', '.docx', '.fb2', '.epub', '.md')
BOOKS_DIR = 'BooksForRAG'
MAX_LINKS = 10

os.makedirs(BOOKS_DIR, exist_ok=True)

def is_book_url(url):
    u = url.lower()
    return u.endswith(TARGET_FORMATS) or any((f'filetype:{ext[1:]}' in u) for ext in TARGET_FORMATS)

def get_yandex_links(query, max_links=20):
    headers = {
        "User-Agent": UserAgent().chrome
    }
    url = 'https://yandex.ru/search/'
    params = {'text': query, 'lr': '213'}
    response = requests.get(url, params=params, headers=headers, timeout=20)
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for a in soup.select('a[href^="http"]:not([rel="nofollow"])'):
        href = a.get("href")
        if href and href not in results:
            results.append(href)
            if len(results) >= max_links:
                break
    return results

def extract_book_links(main_url):
    try:
        headers = {"User-Agent": UserAgent().firefox}
        r = requests.get(main_url, headers=headers, timeout=15)
        if not r.ok: return []
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            url = a['href']
            if is_book_url(url):
                if not url.startswith("http"):
                    url = requests.compat.urljoin(main_url, url)
                links.append(url)
        return links
    except Exception:
        return []

def sanitize_fn(s):
    return re.sub(r'[\\/:*?"<>|]+', "_", s)

def download(url, folder):
    try:
        fname = url.split('/')[-1].split('?')[0]
        fname = sanitize_fn(fname)
        path = Path(folder) / fname
        if path.exists():
            print(f"{fname} — уже сохранено.")
            return
        resp = requests.get(url, timeout=30, stream=True)
        with open(path, 'wb') as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        print(f"{fname} — скачано.")
    except Exception as e:
        print(f"Ошибка скачивания {url}: {e}")

def main():
    yandex_links = get_yandex_links("меланхолия", max_links=20)
    print(f"Нашлось первичных ссылок: {len(yandex_links)}")
    found = set()

    for lnk in yandex_links:
        if is_book_url(lnk):
            found.add(lnk)
            if len(found) >= MAX_LINKS: break

    if len(found) < MAX_LINKS:
        for main_url in yandex_links:
            print(f"Парсю: {main_url}")
            links = extract_book_links(main_url)
            for url in links:
                found.add(url)
                if len(found) >= MAX_LINKS: break
            if len(found) >= MAX_LINKS: break
            time.sleep(1)

    if not found:
        print("Ничего не найдено")
        return
    print(f"Итого найдено ссылок на книги: {len(found)}\nКачаю...\n")
    for url in list(found)[:MAX_LINKS]:
        download(url, BOOKS_DIR)
        time.sleep(2)

if __name__ == '__main__':
    main()
