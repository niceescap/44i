from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from .models import Card, CreateSessionResponse, MessageRequest, MessageResponse, RevealRequest, SessionState
from .session_store import Session, SessionStore
from .symbolic import card_info, interpretation

app = FastAPI(title="44 interprètes API", version="1.0.0")
store = SessionStore()

DISCLAIMER = "44 interprètes est une application symbolique et divertissante. Les interprétations ne remplacent pas un avis médical, juridique, financier ou professionnel."
TOP_SLOTS = [f"{letter}1" for letter in "BCDEFGH"]


def state_of(session: Session) -> SessionState:
    cards: list[Card] = []
    for slot, code in session.top.items():
        cards.append(Card(code=code, slot=slot, face="down", **card_info(code)))
    for slot, code in session.revealed.items():
        cards.append(Card(code=code, slot=slot, face="up", **card_info(code)))
    return SessionState(
        session_id=session.id,
        status="active",
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        question=session.question,
        cards=cards,
        available_slots=list(session.top.keys()),
        messages=session.messages,
        summary=session.summary,
    )


def get_session(session_id: str) -> Session:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session inexistante ou expirée")
    return session


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sessions", response_model=CreateSessionResponse, status_code=201)
def create_session() -> CreateSessionResponse:
    session = store.create()
    return CreateSessionResponse(session_id=session.id, expires_at=session.expires_at.isoformat(), state=state_of(session))


@app.get("/api/sessions/{session_id}/state", response_model=SessionState)
def get_state(session_id: str) -> SessionState:
    return state_of(get_session(session_id))


@app.post("/api/sessions/{session_id}/cards/reveal", response_model=SessionState)
def reveal_card(session_id: str, payload: RevealRequest) -> SessionState:
    session = get_session(session_id)
    code = session.top.pop(payload.slot, None)
    if code is None:
        raise HTTPException(status_code=400, detail="Carte indisponible ou déjà révélée")
    column = payload.slot[0]
    row = 2 + sum(1 for slot in session.revealed if slot.startswith(column))
    target = f"{column}{row}"
    session.revealed[target] = code
    # Comme dans le prototype, une nouvelle ligne de distribution apparaît
    # lorsque les cartes de la ligne supérieure ont toutes été choisies.
    if not session.top and session.deck.cards:
        session.top = {f"{letter}1": session.deck.draw() for letter in "BCDEFGH" if session.deck.cards}
    session.summary = interpretation(list(session.revealed.values()))
    return state_of(session)


async def ask_openwebui(session: Session, message: str) -> str | None:
    base = os.getenv("OPENWEBUI_URL", "").rstrip("/")
    token = os.getenv("OPENWEBUI_API_KEY", "")
    model = os.getenv("OPENWEBUI_MODEL", "")
    if not base or not token or not model:
        return None
    prompt = f"Question utilisateur : {message}\nCartes révélées : {interpretation(list(session.revealed.values()))}\nRéponds en français, avec une lecture symbolique et prudente."
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(f"{base}/api/chat/completions", headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7})
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content")


@app.post("/api/sessions/{session_id}/messages", response_model=MessageResponse)
async def message(session_id: str, payload: MessageRequest) -> MessageResponse:
    session = get_session(session_id)
    text = payload.message.strip()
    if not session.question:
        session.question = text
    session.messages.append({"role": "user", "content": text})
    try:
        answer = await ask_openwebui(session, text)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        answer = None
    if not answer:
        answer = "L’oracle vous invite à observer les symboles révélés et ce qu’ils éveillent en vous.\n\n" + (session.summary or "Révélez une carte pour commencer la lecture.")
    session.messages.append({"role": "oracle", "content": answer})
    return MessageResponse(content=answer)


@app.get("/api/sessions/{session_id}/export", response_class=PlainTextResponse)
def export_session(session_id: str) -> PlainTextResponse:
    session = get_session(session_id)
    lines = ["# 44 interprètes", "", "Consultation symbolique anonyme", "", f"Date : {datetime.now().astimezone().isoformat(timespec='minutes')}", "", "## Avertissement", "", DISCLAIMER, "", "## Question initiale", "", session.question or "_(Aucune question renseignée.)_", "", "## Cartes révélées", ""]
    if session.revealed:
        lines.extend(f"- {slot} → {card_info(code)['name']} ({code})" for slot, code in session.revealed.items())
    else:
        lines.append("_(Aucune carte révélée.)_")
    lines.extend(["", "## Interprétations", "", session.summary or "_(Aucune interprétation disponible.)_", "", "## Échanges avec l’oracle", ""])
    for item in session.messages:
        lines.extend([f"**{'Utilisateur' if item['role'] == 'user' else 'Oracle'} :**", "", item["content"], ""])
    lines.extend(["## Résumé symbolique", "", session.summary or "_(Aucun résumé disponible.)_", ""])
    return PlainTextResponse("\n".join(lines), media_type="text/markdown", headers={"Content-Disposition": 'attachment; filename="44-interpretes-consultation.md"'})


@app.post("/api/sessions/{session_id}/reset", response_model=CreateSessionResponse)
def reset_session(session_id: str) -> CreateSessionResponse:
    if not store.get(session_id):
        raise HTTPException(status_code=404, detail="Session inexistante ou expirée")
    session = store.reset(session_id)
    assert session is not None
    return CreateSessionResponse(session_id=session.id, expires_at=session.expires_at.isoformat(), state=state_of(session))


@app.get("/api/symbolique/card")
def symbolic_card(code: str = Query(pattern=r"^(10|[A2-9JQK])[CDHS]$")) -> dict[str, str]:
    return {"code": code.upper(), **card_info(code)}


@app.get("/api/symbolique/session/{session_id}/summary")
def symbolic_summary(session_id: str) -> dict[str, str]:
    session = get_session(session_id)
    return {"summary": session.summary or interpretation(list(session.revealed.values()))}
