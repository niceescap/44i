from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .deck import Deck

TTL_MINUTES = 45


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Session:
    id: str
    created_at: datetime
    expires_at: datetime
    deck: Deck = field(default_factory=Deck)
    top: dict[str, str] = field(default_factory=dict)
    revealed: dict[str, str] = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)
    question: str | None = None
    summary: str = ""

    def touch(self) -> None:
        self.expires_at = now() + timedelta(minutes=TTL_MINUTES)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def create(self) -> Session:
        with self._lock:
            session = Session(
                id=secrets.token_urlsafe(24),
                created_at=now(),
                expires_at=now() + timedelta(minutes=TTL_MINUTES),
            )
            session.top = {f"{letter}1": session.deck.draw() for letter in "BCDEFGH"}
            self._sessions[session.id] = session
            return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if session.expires_at <= now():
                del self._sessions[session_id]
                return None
            session.touch()
            return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def reset(self, session_id: str) -> Session | None:
        self.delete(session_id)
        return self.create()
