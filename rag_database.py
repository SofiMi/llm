import logging
import re
import signal
import time
from typing import List, Dict, Any, Optional

import chromadb
from sentence_transformers import SentenceTransformer

CHUNK_SIZE = 900
CHUNK_OVERLAP = 180
BATCH_SIZE = 8
MIN_CHUNK_LEN = 50
MAX_CHUNK_LEN = 2048

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("unidb")

def clean(text: str) -> str:
    txt = re.sub(r'\s+', ' ', text)
    return re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\/\%\=\+\*\&\#\@]', '', txt).strip()

def split_chunks(text: str, sz=CHUNK_SIZE, ovl=CHUNK_OVERLAP, max_chunk=MAX_CHUNK_LEN) -> List[str]:
    res = []
    p, n = 0, len(text)
    while p < n:
        end = min(p+sz, n)
        dot = text.rfind('.', p, min(end+70, n))
        if dot > p:
            end = dot+1
        chunk = text[p:end].strip()
        while len(chunk) > 0:
            part = chunk[:max_chunk]
            if len(part) >= MIN_CHUNK_LEN:
                res.append(part)
            chunk = chunk[max_chunk:]
        p = end-ovl if end < n else end
    return res


class RagDB:
    def __init__(self, db: str = "./chroma_db", name: str = "papers", model: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.vec = SentenceTransformer(model, device='cpu')
        self.chroma = chromadb.PersistentClient(path=db)
        try:
            self.col = self.chroma.get_collection(name)
        except Exception:
            self.col = self.chroma.create_collection(name=name, metadata={"description": "Universal RAG DB"})
        log.info(f"Embedding: {model}, Collection: {name}")

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, source_name: Optional[str] = None):
        start = time.time()
        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]
        assert len(texts) == len(metadatas), "texts and metadatas should have same length"
        log.info(f"Добавляется {len(texts)} элементов...")
        ids_all, docs_all, metas_all = [], [], []
        count_chunks = 0
        for idx, (raw_text, meta) in enumerate(zip(texts, metadatas)):
            cln = clean(raw_text)
            chunks = split_chunks(cln)
            for i, chunk in enumerate(chunks):
                ids_all.append(f"{source_name or 'external'}_{idx}_{i}_{int(time.time()*1000)%100000}")
                docs_all.append(chunk)
                m = dict(meta)
                m["source"] = source_name or meta.get('source', 'external')
                m["orig_id"] = idx
                m["chunk_id"] = i
                m["length"] = len(chunk)
                metas_all.append(m)
            count_chunks += len(chunks)
        log.info(f"Всего чанков к индексации: {len(docs_all)}")
        for i in range(0, len(docs_all), BATCH_SIZE):
            batch = docs_all[i:i+BATCH_SIZE]
            batch_ids = ids_all[i:i+BATCH_SIZE]
            batch_metas = metas_all[i:i+BATCH_SIZE]
            embeds = self.vec.encode(batch, convert_to_numpy=True, show_progress_bar=False)
            self.col.add(embeddings=embeds.tolist(), documents=batch, metadatas=batch_metas, ids=batch_ids)
            log.info(f"    Индексировано чанков: {i+len(batch)}/{len(docs_all)}")
        log.info(f"Загрузка завершена за {time.time()-start:.2f} сек.")

    def add_documents(self, docs: List[Dict[str, Any]], text_key: str = "text"):
        texts = [d[text_key] for d in docs]
        metadatas = [d.get("meta", {}) for d in docs]
        self.add_texts(texts, metadatas)

    def query(self, text: str, topk: int = 5):
        e = self.vec.encode([text])
        r = self.col.query(query_embeddings=e.tolist(), n_results=topk)
        return [{
            "doc": r['documents'][0][i],
            "meta": r['metadatas'][0][i],
            "score": r['distances'][0][i] if 'distances' in r else None,
            "id": r['ids'][0][i]
        } for i in range(len(r['documents'][0]))]

    def stats(self):
        docs = self.col.get()
        src = set(m.get('source','unkn') for m in docs.get('metadatas',[]) if isinstance(m,dict))
        return {"total_chunks":self.col.count(), "sources":list(src), "collection":self.col.name}

if __name__ == "__main__":
    rag = RagDB()
    tg_texts = ["Пример поста 1...", "Пост 2...", "Еще пост"]
    tg_metas = [{"source":"t.me/foo", "date":"2024-06-07", "post_id":123}]
    rag.add_texts(tg_texts, metadatas=[{"source": "t.me/channel"} for _ in tg_texts], source_name="t.me/channel")

    print(rag.stats())
    print(rag.query("пример поиска"))
