from langchain_mistralai.chat_models import ChatMistralAI
try:
    from langchain_core.prompts import PromptTemplate
except ImportError:
    from langchain.prompts import PromptTemplate

import rag_database


class RAGBot:
    def __init__(self, api_key, db, mistral_model="mistral-small"):
        self.llm = ChatMistralAI(model=mistral_model, mistral_api_key=api_key)
        self.db = db
        self.prompt = PromptTemplate.from_template(
            "Контекст:\n{context}\n\nВопрос: {question}\n\nОтвет:"
        )

    def query(self, question: str, topk: int = 5) -> str:
        docs = self.db.query(question, topk=topk)
        context = "\n\n".join(doc["doc"] for doc in docs)
        prompt_message = self.prompt.format(context=context, question=question)
        result = self.llm.invoke(prompt_message)
        return getattr(result, "content", None) or getattr(result, "text", None) or str(result)

    def add_session_chunk(self, text, session_id, source_type, source, username, tags=None, **kwargs):
        meta = {
            "session_id": session_id,
            "source_type": source_type,
            "source": source,
            "username": username,
            "tags": tags or []
        }
        meta.update(kwargs)
        self.db.add_texts([text], metadatas=[meta])

    def summarize_session(self, session_id, username, tags=None):
        session_docs = self.db.query(
            text="", topk=100,
            session_id=session_id,
            tags=tags,
            username=username
        )
        self.db.col.delete(where={"session_id": session_id, "source_type": "summary"})
        context = "\n".join(doc["doc"] for doc in session_docs if doc["meta"].get("source_type") != "summary")

        if not context.strip():
            return

        summary_prompt = (
            "Суммируй следующую переписку или сообщения (оставь главное, убери детали):\n"
            f"{context}\n\nИтоговое резюме:"
        )
        summary_text = self.llm.invoke(summary_prompt)
        summary_text = getattr(summary_text, "content", None) or getattr(summary_text, "text", None) or str(summary_text)

        summary_meta = {
            "session_id": session_id,
            "source_type": "summary",
            "source": "summary_bot",
            "tags": tags or [],
            "username": username,
            "updated_at": datetime.now().isoformat()
        }
        self.db.add_texts([summary_text], metadatas=[summary_meta])

if __name__ == "__main__":
    db = rag_database.RagDB(db="./chroma_db", name="papers")
    api_key = ''
    bot = RAGBot(api_key, db)
    answer = bot.query("Что такое ровер?")
    print(answer)
