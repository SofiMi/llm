import logging
import re
import time
from typing import List, Dict, Any, Optional

import chromadb
from sentence_transformers import SentenceTransformer

CHUNK_SIZE = 5000
CHUNK_OVERLAP = 180
BATCH_SIZE = 1
MIN_CHUNK_LEN = 50
MAX_CHUNK_LEN = 2048
MAX_TOTAL_CHUNKS = 500

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("unidb")

def clean(text: str) -> str:
    txt = re.sub(r'\s+', ' ', text)
    return re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\/\%\=\+\*\&\#\@]', '', txt).strip()

def split_chunks(text: str, sz=CHUNK_SIZE, ovl=CHUNK_OVERLAP, min_chunk=MIN_CHUNK_LEN) -> List[str]:
    text = text.strip()
    if len(text) <= sz:
        return [text] if len(text) >= min_chunk else []
    res = []
    n = len(text)
    p = 0
    while p < n:
        end = min(p+sz, n)
        chunk = text[p:end].strip()
        if len(chunk) >= min_chunk:
            res.append(chunk)
        p = end-ovl if end < n else end
    return res

class RagDB:
    def __init__(
        self,
        db: str = "./chroma_db",
        name: str = "papers",
        model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        self.vec = SentenceTransformer(model, device='cpu')
        self.chroma = chromadb.PersistentClient(path=db)
        try:
            self.col = self.chroma.get_collection(name)
        except Exception:
            self.col = self.chroma.create_collection(name=name, metadata={"description": "Universal RAG DB"})
        log.info(f"Embedding: {model}, Collection: {name}")

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        source_name: Optional[str] = None
    ):
        """
        Сохраняет ВСЮ информацию из постов в бд — каждый пост делится на оптимальные чанки.
        В памяти никогда не держится больше одного батча.
        """
        start = time.time()
        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]
        assert len(texts) == len(metadatas), "texts and metadatas should have same length"
        log.info(f"Добавляется {len(texts)} элементов...")

        def chunk_generator(texts, metadatas):
            for idx, (raw_text, meta) in enumerate(zip(texts, metadatas)):
                cln = clean(raw_text)
                chunks = split_chunks(cln)
                if not chunks:
                    log.warning(f"Пустой результат split_chunks для {idx}!")
                for i, chunk in enumerate(chunks):
                    log.info(f"chunklen={len(chunk)} (orig text len: {len(cln)}) [idx={idx}]")

                    id_ = f"{source_name or 'external'}_{idx}_{i}_{int(time.time()*1000)%100000}"
                    m = dict(meta)
                    m["source"] = source_name or meta.get('source', 'external')
                    m["orig_id"] = idx
                    m["chunk_id"] = i
                    m["length"] = len(chunk)
                    yield id_, chunk, m

        ids_buffer, docs_buffer, metas_buffer = [], [], []
        total_chunks = 0
        indexed_count = 0

        for id_, doc, meta in chunk_generator(texts, metadatas):
            ids_buffer.append(id_)
            docs_buffer.append(doc)
            metas_buffer.append(meta)
            total_chunks += 1
            if len(docs_buffer) >= BATCH_SIZE:
                embeds = self.vec.encode(
                    docs_buffer, convert_to_numpy=True, show_progress_bar=False
                )
                self.col.add(
                    embeddings=embeds.tolist(),
                    documents=docs_buffer,
                    metadatas=metas_buffer,
                    ids=ids_buffer
                )
                indexed_count += len(docs_buffer)
                log.info(f"    Индексировано чанков: {indexed_count}/{total_chunks}")
                ids_buffer, docs_buffer, metas_buffer = [], [], []
        if docs_buffer:
            embeds = self.vec.encode(
                docs_buffer, convert_to_numpy=True, show_progress_bar=False
            )
            self.col.add(
                embeddings=embeds.tolist(),
                documents=docs_buffer,
                metadatas=metas_buffer,
                ids=ids_buffer
            )
            indexed_count += len(docs_buffer)
            log.info(f"    Индексировано чанков: {indexed_count}/{total_chunks}")
        log.info(f"Всего чанков к индексации: {total_chunks}")
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
