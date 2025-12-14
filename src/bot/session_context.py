"""
Менеджер контекста сессии для LLM бота
Управляет историей диалога с умным сжатием контекста
"""
from typing import List, Dict, Optional
from datetime import datetime
import json
from dataclasses import dataclass, asdict


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime
    message_id: Optional[int] = None


class SessionContextManager:
    """Менеджер контекста диалоговой сессии"""

    def __init__(self, max_recent_messages: int = 6, max_context_length: int = 3000):
        """
        Args:
            max_recent_messages: Количество последних сообщений для полного хранения
            max_context_length: Максимальная длина итогового контекста в символах
        """
        self.messages: List[Message] = []
        self.max_recent_messages = max_recent_messages
        self.max_context_length = max_context_length
        self.session_summary = ""

    def add_message(self, role: str, content: str, message_id: Optional[int] = None):
        """Добавить сообщение в контекст"""
        message = Message(
            role=role,
            content=content.strip(),
            timestamp=datetime.now(),
            message_id=message_id
        )

        # Добавляем сообщение
        self.messages.append(message)

        # Управляем размером контекста
        self._manage_context_size()

    def _manage_context_size(self):
        """Умное управление размером контекста"""
        if len(self.messages) <= self.max_recent_messages:
            return

        # Если сообщений много, сжимаем старые
        old_messages = self.messages[:-self.max_recent_messages]
        recent_messages = self.messages[-self.max_recent_messages:]

        # Создаем краткое резюме старых сообщений
        if old_messages:
            self.session_summary = self._create_summary(old_messages)

        # Оставляем только недавние сообщения
        self.messages = recent_messages

    def _create_summary(self, messages: List[Message]) -> str:
        """Создать краткое резюме сообщений"""
        if not messages:
            return ""

        user_messages = [m.content for m in messages if m.role == "user"]
        assistant_messages = [m.content for m in messages if m.role == "assistant"]

        # Простое извлечение ключевых тем
        topics = []
        for msg in user_messages:
            if len(msg) > 10:  # Игнорируем очень короткие сообщения
                # Извлекаем первые слова как тему
                words = msg.split()[:8]
                if len(words) >= 3:
                    topics.append(" ".join(words) + "...")

        summary_parts = []
        if topics:
            summary_parts.append(f"Обсуждались темы: {'; '.join(topics[:3])}")

        if len(messages) > 3:
            summary_parts.append(f"Всего в диалоге было {len(user_messages)} вопросов пользователя")

        return ". ".join(summary_parts) if summary_parts else "Начальная часть диалога"

    def get_context_for_llm(self) -> str:
        """Получить контекст для отправки в LLM"""
        context_parts = []

        # Добавляем резюме предыдущего контекста, если есть
        if self.session_summary:
            context_parts.append(f"[Ранее в диалоге: {self.session_summary}]")

        # Добавляем недавние сообщения
        if self.messages:
            context_parts.append("\n--- Текущий контекст диалога ---")
            for msg in self.messages:
                role_name = "Пользователь" if msg.role == "user" else "Ассистент"
                context_parts.append(f"{role_name}: {msg.content}")

        full_context = "\n".join(context_parts)

        # Обрезаем контекст, если он слишком длинный
        if len(full_context) > self.max_context_length:
            # Сохраняем резюме и обрезаем старые сообщения
            if self.session_summary:
                summary_part = f"[Ранее в диалоге: {self.session_summary}]\n"
                available_length = self.max_context_length - len(summary_part) - 100
            else:
                summary_part = ""
                available_length = self.max_context_length - 100

            # Берем последние сообщения, которые помещаются в лимит
            recent_context = ""
            for msg in reversed(self.messages):
                role_name = "Пользователь" if msg.role == "user" else "Ассистент"
                msg_text = f"{role_name}: {msg.content}\n"
                if len(recent_context) + len(msg_text) > available_length:
                    break
                recent_context = msg_text + recent_context

            full_context = summary_part + "--- Текущий контекст диалога ---\n" + recent_context

        return full_context.strip()

    def get_recent_user_messages(self, count: int = 3) -> List[str]:
        """Получить последние сообщения пользователя для формирования запроса"""
        user_messages = [
            msg.content for msg in self.messages
            if msg.role == "user"
        ]
        return user_messages[-count:] if user_messages else []

    def clear_session(self):
        """Очистить сессию"""
        self.messages.clear()
        self.session_summary = ""

    def get_session_stats(self) -> Dict:
        """Получить статистику сессии"""
        user_count = sum(1 for m in self.messages if m.role == "user")
        assistant_count = sum(1 for m in self.messages if m.role == "assistant")

        return {
            "total_messages": len(self.messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "has_summary": bool(self.session_summary),
            "context_length": len(self.get_context_for_llm())
        }

    def to_dict(self) -> Dict:
        """Сериализация для хранения в FSMContext"""
        return {
            "messages": [asdict(msg) for msg in self.messages],
            "session_summary": self.session_summary,
            "max_recent_messages": self.max_recent_messages,
            "max_context_length": self.max_context_length
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SessionContextManager":
        """Десериализация из FSMContext"""
        instance = cls(
            max_recent_messages=data.get("max_recent_messages", 6),
            max_context_length=data.get("max_context_length", 3000)
        )

        instance.session_summary = data.get("session_summary", "")

        # Восстанавливаем сообщения
        for msg_data in data.get("messages", []):
            msg = Message(
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                message_id=msg_data.get("message_id")
            )
            instance.messages.append(msg)

        return instance
