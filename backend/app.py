from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .models import Card, CreateSessionResponse, MessageRequest, MessageResponse, RevealRequest, SessionState
from .llm_handler_v2 import cold_start_message, complete
from .rosace_dealer import RosaceStore
from .session_store import Session, SessionStore
from .symbolic import CARDS, QUALITIES, card_info, interpretation, pair_symbol

app = FastAPI(title="La Rosace API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = SessionStore()
rosace_store = RosaceStore()

REPO_ROOT = Path(__file__).resolve().parents[1]

WEB_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

DISCLAIMER = "La Rosace est une application symbolique et divertissante. Les interprétations ne remplacent pas un avis médical, juridique, financier ou professionnel."
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
        column_signal=session.column_signal,
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
async def create_session() -> CreateSessionResponse:
    session = store.create()
    try:
        result = await ask_openwebui(session, "")
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[openwebui] appel échoué: {type(exc).__name__}: {exc}", flush=True)
        result = None
    apply_command(session, result)
    session.messages.append({"role": "oracle", "content": result["Chat"] if result else fallback_oracle(session, "")})
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
    column = session.active_col
    row = 2 + session.column_count(column)
    target = f"{column}{row}"
    session.revealed[target] = code
    symbolic_result = session.symbolic.process(code, list(session.revealed.values()), session.active_col, row)
    session.last_symbolic_event = symbolic_result.get("event", {})
    session.column_signal = symbolic_result.get("signal")
    # Garde-fou absolu si le moteur n'a pas émis de signal (row 11 = limite engine)
    if row >= 11 and not session.column_signal:
        session.column_signal = "obligation:cloture_immediate"
    session.summary = symbolic_result.get("summary", session.summary)
    if not session.top and session.deck.cards:
        session.top = {f"{letter}1": session.deck.draw() for letter in "BCDEFGH" if session.deck.cards}
    try:
        result = await ask_openwebui(session, "")
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[openwebui] échec après révélation: {exc}", flush=True)
        result = None
    apply_command(session, result)
    answer = result["Chat"] if result else fallback_oracle(session, "")
    session.messages.append({"role": "oracle", "content": answer})
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
        "theme_proposal": session.last_symbolic_event.get("theme_proposal", ""),
        "themes_precedents": session.themes,
        "historique_recent": session.messages[-10:],
        "colonne_active": session.active_col,
        "signal_colonne": session.column_signal,
        "dernier_evenement_symbolique": session.last_symbolic_event,
        "contraintes": {
            "lecture_symbolique": True,
            "prediction_certaine": False,
            "langue": "fr",
        },
    }


def apply_command(session: Session, result: dict[str, Any] | None) -> None:
    """Applique uniquement la commande de colonne validée par le backend."""
    forced = bool(session.column_signal and session.column_signal.startswith("obligation:"))
    if not forced and (not result or result.get("Com") != "tx"):
        return
    next_column = session.next_column()
    if next_column is None:
        return
    theme = (result.get("Theme", "") if result else "").strip()
    if not theme and session.last_symbolic_event.get("type") == "theme":
        theme = session.last_symbolic_event.get("theme_proposal", "")
    if theme:
        session.themes.append(theme)
    session.active_col = next_column
    session.column_signal = None


def fallback_oracle(session: Session, message: str) -> str:
    """Réponse locale non silencieuse lorsque OpenWebUI échoue ou est lent."""
    cards = list(session.revealed.values())
    context = interpretation(cards) if cards else "Aucune carte n’est encore révélée."
    if not cards:
        return "Le tapis est prêt. Choisis une carte face cachée pour commencer la lecture symbolique."
    if message:
        return (
            "Je garde ta question au centre de la consultation. Les cartes révélées "
            "proposent des symboles à explorer, pas une réponse certaine.\n\n"
            f"{context}\n\n"
            "Observe ce qui résonne dans ta situation, puis choisis une nouvelle carte "
            "si tu souhaites approfondir le contexte."
        )
    return (
        "Une nouvelle carte vient d’entrer dans le contexte du tirage. "
        "Voici les symboles actuellement présents :\n\n"
        f"{context}\n\n"
        "Que fait émerger cette combinaison pour toi ? Tu peux me répondre ou "
        "choisir une autre carte face cachée."
    )


def parse_masterout(content: Any) -> dict[str, Any] | None:
    # Certains endpoints OpenAI-compatible renvoient parfois des segments de
    # contenu au lieu d'une chaîne unique.
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    if not isinstance(content, str):
        return None
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").replace("json\n", "", 1).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        # Certains modèles ajoutent une phrase avant/après le JSON.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        value = None
        if start >= 0 and end > start:
            try:
                value = json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                value = None
        if value is None:
            # Laguna peut occasionnellement répondre en texte malgré le contrat
            # JSON. On conserve alors sa réponse plutôt que de la perdre.
            return {"Chat": content.strip(), "Com": "no", "Theme": "", "Sources": []} if content.strip() else None
    if not isinstance(value, dict) or not value.get("Chat"):
        return None
    command = str(value.get("Com", "no")).lower()
    value["Com"] = command if command in {"no", "tx"} else "no"
    value["Theme"] = str(value.get("Theme", ""))
    value["Sources"] = value.get("Sources", []) if isinstance(value.get("Sources", []), list) else []
    return value


def execute_symbolic_tool(name: str, arguments: dict[str, Any]) -> str:
    """Exécute une recherche read-only lorsque OpenWebUI renvoie un tool call."""
    code = str(arguments.get("code", "")).strip().upper()
    if name == "rechercher_carte":
        item = CARDS.get(code)
        return json.dumps({"code": code, "found": bool(item), "source": "52cartes.json", "card": item or {}}, ensure_ascii=False)
    if name == "rechercher_paire":
        first = str(arguments.get("carte_a", arguments.get("card_a", ""))).strip().upper()
        second = str(arguments.get("carte_b", arguments.get("card_b", ""))).strip().upper()
        result = pair_symbol(first, second)
        result["interpretation"] = interpretation([first, second])
        return json.dumps(result, ensure_ascii=False)
    if name == "rechercher_qualite":
        base = str(arguments.get("carte_base", "")).strip().upper()
        apport = str(arguments.get("carte_apport", "")).strip().upper()
        key = f"{base}|{apport[-1]}" if apport else ""
        return json.dumps({"cards": [base, apport], "quality": QUALITIES.get(key, {}), "source": "qualites.json"}, ensure_ascii=False)
    if name == "rechercher_remarquables":
        values = arguments.get("cartes", "")
        values = values if isinstance(values, list) else str(values).split(",")
        return json.dumps({"cards": [str(value).strip().upper() for value in values if str(value).strip()], "remarkables": [], "source": "detector_rem.py"}, ensure_ascii=False)
    return json.dumps({"error": f"Outil inconnu: {name}"}, ensure_ascii=False)


async def ask_openwebui(session: Session, message: str) -> dict[str, Any] | None:
    """Appel OpenWebUI avec boucle native tool_call -> résultat -> réponse finale."""
    base = os.getenv("OPENWEBUI_URL", "").rstrip("/")
    token = os.getenv("OPENWEBUI_API_KEY", "")
    model = os.getenv("OPENWEBUI_MODEL", "44-interpretes")
    if not base or not token:
        return None
    tool_ids = [item.strip() for item in os.getenv("OPENWEBUI_TOOL_IDS", "").split(",") if item.strip()]
    conversation: list[dict[str, Any]] = [{"role": "user", "content": json.dumps(masterin(session, message), ensure_ascii=False)}]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=90) as client:
        for iteration in range(4):
            body: dict[str, Any] = {"model": model, "messages": conversation, "temperature": 0.55, "max_tokens": 1200, "stream": False}
            if tool_ids:
                body["tool_ids"] = tool_ids
            response = await client.post(f"{base}/api/chat/completions", headers=headers, json=body)
            if response.status_code >= 400:
                print(f"[openwebui] HTTP {response.status_code}: {response.text[:800]}", flush=True)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            choice = data.get("choices", [{}])[0]
            assistant = choice.get("message", {}) if isinstance(choice, dict) else {}
            tool_calls = assistant.get("tool_calls") or []
            content = assistant.get("content")

            if content:
                result = parse_masterout(content)
                if result:
                    return result

            if not tool_calls:
                print(f"[openwebui] réponse sans masterout après {iteration + 1} itération(s)", flush=True)
                return parse_masterout(content)

            print(f"[openwebui] exécution de {len(tool_calls)} tool_call(s), tour {iteration + 1}", flush=True)
            conversation.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name", "")
                raw_arguments = function.get("arguments", "{}")
                try:
                    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                except json.JSONDecodeError:
                    arguments = {}
                tool_result = execute_symbolic_tool(name, arguments if isinstance(arguments, dict) else {})
                conversation.append({"role": "tool", "tool_call_id": call.get("id", name), "name": name, "content": tool_result})

    print("[openwebui] boucle tool_call épuisée", flush=True)
    return None


@app.post("/api/sessions/{session_id}/messages", response_model=MessageResponse)
async def message(session_id: str, payload: MessageRequest) -> MessageResponse:
    session = get_session(session_id)
    text = payload.message.strip()
    if not session.question:
        session.question = text
    session.messages.append({"role": "user", "content": text})
    try:
        result = await ask_openwebui(session, text)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[openwebui] échec message: {exc}", flush=True)
        result = None
    apply_command(session, result)
    answer = result["Chat"] if result else fallback_oracle(session, text)
    session.messages.append({"role": "oracle", "content": answer})
    return MessageResponse(content=answer)


@app.get("/api/sessions/{session_id}/export", response_class=PlainTextResponse)
def export_session(session_id: str) -> PlainTextResponse:
    session = get_session(session_id)
    lines = ["# La Rosace", "", "Consultation Symbolique anonyme", "", f"Code de session : {session.id}", f"Date : {datetime.now().astimezone().strftime('%d/%m/%Y %H:%M')}", "", "## Avertissement", "", DISCLAIMER, "", "## Question initiale", "", session.question or "_(Aucune question renseignée.)_", "", "## Cartes révélées", ""]
    if session.revealed:
        lines.extend(f"- {slot} → {card_info(code)['name']} ({code})" for slot, code in session.revealed.items())
    else:
        lines.append("_(Aucune carte révélée.)_")
    lines.extend(["", "## Interprétations", "", session.summary or "_(Aucune interprétation disponible.)_", "", "## Échanges avec l’oracle", ""])
    for item in session.messages:
        lines.extend([f"**{'Utilisateur' if item['role'] == 'user' else 'Oracle'} :**", "", item["content"], ""])
    lines.extend(["## Résumé symbolique", "", session.summary or "_(Aucun résumé disponible.)_", ""])
    # BOM UTF-8 : certains éditeurs anciens sinon interprètent le Markdown en Windows-1252.
    return PlainTextResponse("\ufeff" + "\n".join(lines), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="la-rosace-consultation.md"'})


@app.post("/api/sessions/{session_id}/reset", response_model=CreateSessionResponse)
def reset_session(session_id: str) -> CreateSessionResponse:
    if not store.get(session_id):
        raise HTTPException(status_code=404, detail="Session inexistante ou expirée")
    session = store.reset(session_id)
    assert session is not None
    return CreateSessionResponse(session_id=session.id, expires_at=session.expires_at.isoformat(), state=state_of(session))


@app.get("/api/symbolique/card")
def symbolic_card(code: str = Query(pattern=r"^(T|[A2-9JQK])[CDHS]$")) -> dict[str, str]:
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


# ---------- Workflow v2 : rosace 52 + 3 clics + brut testeur_query ----------

class V2CreateRequest(BaseModel):
    stage_width: float = 360
    stage_height: float = 360


class V2RevealRequest(BaseModel):
    site_id: int = Field(ge=0, le=51)


def _rosace_session(session_id: str):
    session = rosace_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session inexistante ou expirée")
    return session


@app.get("/rosace", include_in_schema=False)
def rosace_page() -> FileResponse:
    html = REPO_ROOT / "rosace_depose.html"
    if not html.exists():
        raise HTTPException(status_code=404, detail="rosace_depose.html introuvable")
    return FileResponse(html)


@app.post("/api/v2/sessions")
def v2_create_session(payload: V2CreateRequest | None = None) -> dict[str, Any]:
    body = payload or V2CreateRequest()
    session = rosace_store.create(body.stage_width, body.stage_height)
    return session.public_state()


@app.get("/api/v2/sessions/{session_id}")
def v2_get_session(session_id: str) -> dict[str, Any]:
    return _rosace_session(session_id).public_state()


@app.post("/api/v2/sessions/{session_id}/reveal")
def v2_reveal(session_id: str, payload: V2RevealRequest) -> dict[str, Any]:
    try:
        session = rosace_store.reveal(session_id, payload.site_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session inexistante ou expirée")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return session.public_state()


@app.post("/api/v2/sessions/{session_id}/interpret")
async def v2_interpret(session_id: str) -> dict[str, Any]:
    session = _rosace_session(session_id)
    if session.phase != "oracle":
        raise HTTPException(status_code=400, detail="L'interprétation suit la troisième carte")
    if session.interpreted and session.messages:
        last = next((m for m in reversed(session.messages) if m.get("role") == "oracle"), None)
        return {"content": last["content"] if last else "", "messages": session.messages}
    logs = session.pipeline.logs()
    if not session.llm_messages:
        session.llm_messages.append({"role": "user", "content": cold_start_message(logs)})
    try:
        reply = await complete(session.llm_messages)
    except Exception as exc:
        print(f"[llm_v2] interprétation échouée: {exc}", flush=True)
        raise HTTPException(status_code=502, detail="L'oracle est silencieux un instant.")
    session.llm_messages.append({"role": "assistant", "content": reply})
    session.messages.append({"role": "oracle", "content": reply})
    session.interpreted = True
    return {"content": reply, "messages": session.messages}


# ---------- Prospects Premium : clics uniques + e-mails ----------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PROSPECT_LOCK = threading.Lock()


class ProspectClickRequest(BaseModel):
    visitor_id: str = Field(min_length=8, max_length=80)
    session_id: str | None = None


class ProspectEmailRequest(BaseModel):
    visitor_id: str = Field(min_length=8, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    session_id: str | None = None


def _prospect_dir() -> Path:
    preferred = Path(os.getenv("ROSACE_LOG_DIR", "/home/nicee/44i/logs"))
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".writable"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError as exc:
        fallback = REPO_ROOT / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        print(f"[prospects] {preferred} inaccessible ({exc}); fallback {fallback}", flush=True)
        return fallback


def _prospect_path() -> Path:
    return _prospect_dir() / "prospects.json"


def _empty_prospects() -> dict[str, Any]:
    return {
        "updated_at": None,
        "unique_clicks": 0,
        "total_clicks": 0,
        "emails_count": 0,
        "clicks": [],
        "emails": [],
    }


def _load_prospects() -> dict[str, Any]:
    path = _prospect_path()
    if not path.exists():
        return _empty_prospects()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_prospects()
    if not isinstance(data, dict):
        return _empty_prospects()
    data.setdefault("clicks", [])
    data.setdefault("emails", [])
    data.setdefault("unique_clicks", 0)
    data.setdefault("total_clicks", 0)
    data.setdefault("emails_count", 0)
    return data


def _save_prospects(data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = _prospect_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@app.post("/api/v2/prospects/click")
def prospect_click(payload: ProspectClickRequest) -> dict[str, Any]:
    visitor = payload.visitor_id.strip()
    with _PROSPECT_LOCK:
        data = _load_prospects()
        already = any(item.get("visitor_id") == visitor for item in data["clicks"])
        data["clicks"].append({
            "ts": _now_iso(),
            "visitor_id": visitor,
            "session_id": payload.session_id,
            "unique": not already,
        })
        data["total_clicks"] = len(data["clicks"])
        data["unique_clicks"] = sum(1 for item in data["clicks"] if item.get("unique"))
        _save_prospects(data)
    return {"ok": True, "unique": not already, "unique_clicks": data["unique_clicks"]}


@app.post("/api/v2/prospects/email")
def prospect_email(payload: ProspectEmailRequest) -> dict[str, Any]:
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Adresse e-mail invalide")
    visitor = payload.visitor_id.strip()
    with _PROSPECT_LOCK:
        data = _load_prospects()
        already = any(item.get("email") == email for item in data["emails"])
        if not already:
            data["emails"].append({
                "ts": _now_iso(),
                "email": email,
                "visitor_id": visitor,
                "session_id": payload.session_id,
            })
            data["emails_count"] = len(data["emails"])
            _save_prospects(data)
    return {"ok": True, "stored": not already, "emails_count": data["emails_count"]}


@app.post("/api/v2/sessions/{session_id}/messages")
async def v2_message(session_id: str, payload: MessageRequest) -> dict[str, Any]:
    session = _rosace_session(session_id)
    if session.phase != "oracle":
        raise HTTPException(status_code=400, detail="La conversation s'ouvre après la troisième carte")
    text = payload.message.strip()
    if not session.question:
        session.question = text
    session.messages.append({"role": "user", "content": text})
    if not session.llm_messages:
        session.llm_messages.append({"role": "user", "content": cold_start_message(session.pipeline.logs())})
    session.llm_messages.append({"role": "user", "content": text})
    try:
        reply = await complete(session.llm_messages)
    except Exception as exc:
        print(f"[llm_v2] chat échoué: {exc}", flush=True)
        raise HTTPException(status_code=502, detail="L'oracle est silencieux un instant.")
    session.llm_messages.append({"role": "assistant", "content": reply})
    session.messages.append({"role": "oracle", "content": reply})
    session.interpreted = True
    return {"content": reply, "messages": session.messages}
