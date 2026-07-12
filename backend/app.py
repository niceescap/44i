from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .models import Card, CreateSessionResponse, MessageRequest, MessageResponse, RevealRequest, SessionState
from .session_store import Session, SessionStore
from .symbolic import card_info, interpretation

app = FastAPI(title="44 interprètes API", version="1.0.0")
store = SessionStore()

WEB_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

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
        active_column=session.active_col,
        themes=session.themes,
    )




@app.get("/", include_in_schema=False)
def browser_app() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
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
async def reveal_card(session_id: str, payload: RevealRequest) -> SessionState:
    session = get_session(session_id)
    code = session.top.pop(payload.slot, None)
    if code is None:
        raise HTTPException(status_code=400, detail="Carte indisponible ou déjà révélée")
    column = payload.slot[0]
    row = 2 + sum(1 for slot in session.revealed if slot.startswith(column))
    target = f"{column}{row}"
    session.revealed[target] = code
    if not session.top and session.deck.cards:
        session.top = {f"{letter}1": session.deck.draw() for letter in "BCDEFGH" if session.deck.cards}
    session.summary = interpretation(list(session.revealed.values()))
    result = await ask_openwebui(session, "")
    if result:
        session.messages.append({"role": "oracle", "content": result["Chat"]})
    return state_of(session)


def masterin(session: Session, message: str) -> dict[str, Any]:
    revealed = [
        {
            "code": code,
            "valeur": code,
            "slot": slot,
            "emplacement": slot,
            "name": card_info(code)["name"],
            "nom": card_info(code)["name"],
            "symbol": card_info(code)["symbol"],
        }
        for slot, code in session.revealed.items()
    ]
    return {
        "type": "consultation_44i",
        "version": "1",
        "message_utilisateur": message,
        "carte_revelee": revealed[-1] if revealed else None,
        "cartes_revelees": revealed,
        "resume_symbolique": session.summary,
        "themes_precedents": [],
        "historique_recent": session.messages[-10:],
        "contraintes": {
            "lecture_symbolique": True,
            "prediction_certaine": False,
            "langue": "fr",
        },
    }


def parse_masterout(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, str):
        return None
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").replace("json\n", "", 1).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or not value.get("Chat"):
        return None
    command = str(value.get("Com", "no")).lower()
    value["Com"] = command if command in {"no", "tx"} else "no"
    value["Theme"] = str(value.get("Theme", ""))
    value["Sources"] = value.get("Sources", []) if isinstance(value.get("Sources", []), list) else []
    return value


async def ask_openwebui(session: Session, message: str) -> dict[str, Any] | None:
    base = os.getenv("OPENWEBUI_URL", "").rstrip("/")
    token = os.getenv("OPENWEBUI_API_KEY", "")
    model = os.getenv("OPENWEBUI_MODEL", "44-interpretes")
    if not base or not token:
        return None
    tool_ids = [item.strip() for item in os.getenv("OPENWEBUI_TOOL_IDS", "").split(",") if item.strip()]
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": json.dumps(masterin(session, message), ensure_ascii=False)}],
        "temperature": 0.7,
        "stream": False,
    }
    if tool_ids:
        body["tool_ids"] = tool_ids
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{base}/api/chat/completions", headers=headers, json=body)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        return parse_masterout(content)


@app.post("/api/sessions/{session_id}/messages", response_model=MessageResponse)
async def message(session_id: str, payload: MessageRequest) -> MessageResponse:
    session = get_session(session_id)
    text = payload.message.strip()
    if not session.question:
        session.question = text
    session.messages.append({"role": "user", "content": text})
    try:
        result = await ask_openwebui(session, text)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        result = None
    answer = result["Chat"] if result else "L’oracle vous invite à observer les symboles révélés et ce qu’ils éveillent en vous.\n\n" + (session.summary or "Révélez une carte pour commencer la lecture.")
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


@app.get("/api/symbolique/pair")
def symbolic_pair(cards: str = Query(description="Deux codes séparés par une virgule")) -> dict[str, Any]:
    values = [value.strip().upper() for value in cards.split(",") if value.strip()]
    if len(values) != 2:
        raise HTTPException(status_code=400, detail="Deux cartes sont requises")
    return {"cards": [{"code": value, **card_info(value)} for value in values], "interpretation": interpretation(values)}


@app.get("/api/symbolique/remarkables")
def symbolic_remarkables(cards: str = Query(description="Codes séparés par des virgules")) -> dict[str, list[Any]]:
    values = [value.strip().upper() for value in cards.split(",") if value.strip()]
    return {"cards": values, "remarkables": []}


@app.get("/api/symbolique/session/{session_id}/summary")
def symbolic_summary(session_id: str) -> dict[str, str]:
    session = get_session(session_id)
    return {"summary": session.summary or interpretation(list(session.revealed.values()))}
