from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .deck import Deck
from .symbolic_engine import SymbolicEngine

TTL_MINUTES = 45
DRAW_COLUMNS = "ABCDE"
# Garde-fou V1 : sept cartes maximum par colonne pour préserver la lisibilité.
# Les signaux symboliques peuvent clôturer une colonne plus tôt.
HARD_LIMIT = 7


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
    themes: list[str] = field(default_factory=list)
    question: str | None = None
    summary: str = ""
    active_col: str = "A"
    symbolic: SymbolicEngine = field(default_factory=SymbolicEngine)
    column_signal: str | None = None
    last_symbolic_event: dict = field(default_factory=dict)
    # Language is selected once when the anonymous session starts. It is never
    # inferred from message content, which keeps every response consistent.
    language: str = "fr"

    def touch(self) -> None:
        self.expires_at = now() + timedelta(minutes=TTL_MINUTES)

    def column_count(self, column: str) -> int:
        return sum(1 for slot in self.revealed if slot.startswith(column))

    def next_column(self) -> str | None:
        try:
            start = DRAW_COLUMNS.index(self.active_col) + 1
        except ValueError:
            start = 0
        for column in DRAW_COLUMNS[start:]:
            if self.column_count(column) < HARD_LIMIT:
                return column
        return None


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
