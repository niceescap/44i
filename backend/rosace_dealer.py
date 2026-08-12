#!/usr/bin/env python3
"""Croupier v2 — 52 cartes sur la rosace, 3 révélations, pipeline symbolique.

Le client ne reçoit jamais le code d'une carte avant le clic correspondant.
Le mélange utilise SystemRandom. Chaque site reçoit exactement une carte.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .deck import Deck
from .query_pipeline import QueryPipeline
from .rosace_geom import layout, public_sites

TTL_MINUTES = 45
MAX_CHOSEN = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RosaceSession:
    id: str
    created_at: datetime
    expires_at: datetime
    seed: str
    sites: list[dict[str, Any]]
    occupancy: dict[int, str]
    chosen: list[dict[str, Any]] = field(default_factory=list)
    pipeline: QueryPipeline = field(default_factory=QueryPipeline)
    messages: list[dict[str, str]] = field(default_factory=list)
    question: str | None = None

    def touch(self) -> None:
        self.expires_at = _now() + timedelta(minutes=TTL_MINUTES)

    @property
    def phase(self) -> str:
        n = len(self.chosen)
        if n >= MAX_CHOSEN:
            return "oracle"
        if n:
            return "table"
        return "deal"

    def public_state(self) -> dict[str, Any]:
        revealed = {item["site_id"]: item for item in self.chosen}
        sites = []
        for site in public_sites(self.sites):
            hit = revealed.get(site["id"])
            if hit:
                sites.append({
                    **site,
                    "face": "up",
                    "card": hit["card"],
                })
            else:
                sites.append({**site, "face": "down"})
        snap = self.pipeline.snapshot()
        return {
            "session_id": self.id,
            "expires_at": self.expires_at.isoformat(),
            "phase": self.phase,
            "chosen_count": len(self.chosen),
            "sites": sites,
            "chosen": list(self.chosen),
            "symbolique": snap["symbolique"],
            "messages": list(self.messages),
        }


class RosaceStore:
    def __init__(self) -> None:
        self._sessions: dict[str, RosaceSession] = {}
        self._lock = threading.RLock()

    def create(self, stage_w: float = 360.0, stage_h: float = 360.0) -> RosaceSession:
        sites = layout(stage_w, stage_h)
        if len(sites) != 52:
            raise RuntimeError(f"rosace: {len(sites)} sites, 52 attendus")
        deck = Deck()
        if len(deck.cards) != 52:
            raise RuntimeError("deck incomplet")
        occupancy = {site["id"]: deck.cards[i] for i, site in enumerate(sites)}
        if len(set(occupancy.values())) != 52:
            raise RuntimeError("affectation non bijective")
        session = RosaceSession(
            id=secrets.token_urlsafe(24),
            created_at=_now(),
            expires_at=_now() + timedelta(minutes=TTL_MINUTES),
            seed=secrets.token_hex(8),
            sites=sites,
            occupancy=occupancy,
        )
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> RosaceSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if session.expires_at <= _now():
                del self._sessions[session_id]
                return None
            session.touch()
            return session

    def reveal(self, session_id: str, site_id: int) -> RosaceSession:
        session = self.get(session_id)
        if not session:
            raise KeyError("session")
        if len(session.chosen) >= MAX_CHOSEN:
            raise ValueError("trois cartes déjà révélées")
        if site_id not in session.occupancy:
            raise ValueError("site inconnu")
        if any(item["site_id"] == site_id for item in session.chosen):
            raise ValueError("carte déjà révélée")
        code = session.occupancy[site_id]
        snap = session.pipeline.traiter(code)
        session.chosen.append({
            "site_id": site_id,
            "card": code,
            "order": len(session.chosen) + 1,
            "event": snap["symbolique"][-1] if snap["symbolique"] else {},
        })
        return session
