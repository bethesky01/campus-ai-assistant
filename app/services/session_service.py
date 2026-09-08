import logging
from collections import defaultdict
from threading import RLock
from uuid import uuid4

from app.config import get_settings
from app.models.schemas import ChatMessage

logger = logging.getLogger(__name__)


class SessionService:
    """Thread-safe, process-local workshop history. Restarting the app clears it."""
    def __init__(self):
        self._sessions: dict[str, list[ChatMessage]] = defaultdict(list)
        self._lock = RLock()

    def ensure_id(self, session_id: str | None) -> str:
        return session_id or str(uuid4())

    def history(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def add(self, session_id: str, message: ChatMessage) -> None:
        with self._lock:
            messages = self._sessions[session_id]
            messages.append(message)
            del messages[:-get_settings().session_max_messages]
        logger.info("session_message_added session_id=%s role=%s history_size=%d", session_id, message.role, len(messages))

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


session_service = SessionService()
