from __future__ import annotations

from typing import Dict, List
from threading import RLock
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class SessionMemory:
    """
    Simple in-process session memory keyed by a session_id.
    Stores LangChain message objects to feed as chat_history.
    """

    _store: Dict[str, List[BaseMessage]] = {}
    _lock: RLock = RLock()

    @classmethod
    def get(cls, session_id: str) -> List[BaseMessage]:
        with cls._lock:
            return list(cls._store.get(session_id, []))

    @classmethod
    def append_user(cls, session_id: str, content: str) -> None:
        with cls._lock:
            cls._store.setdefault(session_id, []).append(HumanMessage(content=content))

    @classmethod
    def append_ai(cls, session_id: str, content: str) -> None:
        with cls._lock:
            cls._store.setdefault(session_id, []).append(AIMessage(content=content))

    @classmethod
    def clear(cls, session_id: str) -> None:
        with cls._lock:
            if session_id in cls._store:
                del cls._store[session_id]

