from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Card(BaseModel):
    code: str
    slot: str
    face: Literal["up", "down"]
    name: str = ""
    symbol: str = ""


class CreateSessionRequest(BaseModel):
    """Client locale is advisory; the backend only persists a supported language."""

    locale: str = Field(default="fr", min_length=2, max_length=35)


class SessionState(BaseModel):
    session_id: str
    status: Literal["active", "expired"]
    created_at: str
    expires_at: str
    # The API normalizes this to its explicit supported-language allow-list.
    language: str = Field(default="fr", min_length=2, max_length=10)
    question: str | None = None
    cards: list[Card] = Field(default_factory=list)
    available_slots: list[str] = Field(default_factory=list)
    messages: list[dict[str, str]] = Field(default_factory=list)
    summary: str = ""
    active_column: str = "A"
    themes: list[str] = Field(default_factory=list)
    column_signal: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    expires_at: str
    state: SessionState


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    role: Literal["oracle"] = "oracle"
    content: str


class RevealRequest(BaseModel):
    slot: str = Field(pattern=r"^[B-H]1$")
