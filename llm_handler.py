#!/usr/bin/env python3
"""
llm_handler.py — Dame de Trèfle
Construction du contexte symbolique et appel OpenRouter via preset.
Aucun system prompt n'est injecté : le preset @preset/dame-de-trefle
porte la totalité des instructions et du format de réponse.
"""

import json
import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRACTOR_DIR = os.path.join(BASE_DIR, "extractor")

KEY_FILE   = os.path.join(BASE_DIR, "OR_key.txt")
MODEL_FILE = os.path.join(BASE_DIR, "OR_model.txt")


def _load(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return default


API_KEY    = _load(KEY_FILE)
MODEL_NAME = _load(MODEL_FILE)

if not API_KEY or not MODEL_NAME:
    print("⚠ llm_handler: OR_key.txt ou OR_model.txt manquant.", flush=True)


# ---------- ressources symboliques ----------
try:
    with open(os.path.join(EXTRACTOR_DIR, "52cartes.json"), encoding="utf-8") as f:
        CARTES = {c["carte"]: c for c in json.load(f)}
    with open(os.path.join(EXTRACTOR_DIR, "qualites.json"), encoding="utf-8") as f:
        QUALITES = json.load(f)
except Exception as e:
    print(f"⚠ ressources symboliques indisponibles: {e}", flush=True)
    CARTES = {}
    QUALITES = {}


# ---------- mapping noms lisibles de cartes ----------
NOMS_CARTES = {}

# Surcharge éventuelle par le fichier 52cartes.json (prioritaire)
def _load_noms_cartes():
    global NOMS_CARTES
    NOMS_CARTES = {}
    for code, meta in CARTES.items():
        nom = meta.get("nom") or meta.get("intitule") or meta.get("titre")
        if nom:
            NOMS_CARTES[code] = nom

_load_noms_cartes()

# Tables de conversion standard (poker français)
RANKS = {
    "A": "As",
    "K": "Roi",
    "Q": "Dame",
    "J": "Valet",
    "T": "Dix",
    "9": "Neuf",
    "8": "Huit",
    "7": "Sept",
    "6": "Six",
    "5": "Cinq",
    "4": "Quatre",
    "3": "Trois",
    "2": "Deux",
}
SUITS = {
    "S": "Pique",
    "H": "Cœur",
    "D": "Carreau",
    "C": "Trèfle",
}

def nom_carte(code):
    """Convertit un code carte (ex: 'QC', 'AS', 'Td') en nom lisible (ex: 'Dame de Trèfle', 'As de Pique')."""
    if not code or len(code) < 2:
        return code or ""

    code = code.strip().upper()
    if len(code) < 2:
        return code

    # Priorité au nom issu de 52cartes.json s'il existe
    if code in NOMS_CARTES:
        return NOMS_CARTES[code]

    rank_part = code[:-1]      # tout sauf la dernière lettre
    suit_letter = code[-1]     # dernière lettre

    rank = RANKS.get(rank_part, rank_part)
    suit = SUITS.get(suit_letter, suit_letter)

    return f"{rank} de {suit}"


# ---------- ChromaDB ----------
try:
    import chromadb
    chroma_client = chromadb.PersistentClient(path=os.path.join(EXTRACTOR_DIR, "chroma_db"))
    col_paires = chroma_client.get_collection("paires")
except Exception as e:
    col_paires = None
    print(f"⚠ collection ChromaDB indisponible: {e}", flush=True)


sys.path.insert(0, EXTRACTOR_DIR)
try:
    from detector_rem import detecter_remarquables
except Exception:
    def detecter_remarquables(*args, **kwargs):
        return []


# ---------- état symbolique ----------
_symbolique = []
_etat = {"etape": "designation", "precedente": None, "posees": []}


def reset_symbolique():
    global _symbolique, _etat
    _symbolique = []
    _etat = {"etape": "designation", "precedente": None, "posees": []}


def _fetch_paire(c1, c2):
    if not col_paires:
        return ""
    pid = "|".join(sorted([c1, c2]))
    try:
        r = col_paires.get(ids=[pid], include=["documents"])
        if r.get("documents") and r["documents"][0]:
            return r["documents"][0]
    except Exception:
        pass
    return ""


def _fetch_qualite(base, apport):
    cle = f"{base}|{apport[-1]}"
    q = QUALITES.get(cle, {})
    texte = q.get("texte", "")
    qualite = q.get("qualite", "indéfini")
    def_app = CARTES.get(apport, {})
    conclusion = def_app.get(qualite, "") if qualite in ("harmonie", "conflit") else ""
    return {"texte": texte, "qualite": qualite, "conclusion": conclusion}


def traiter_carte(carte):
    if not carte or carte not in CARTES:
        return
    _etat["posees"].append(carte)
    rem = detecter_remarquables(_etat["posees"])

    if _etat["etape"] == "designation":
        _symbolique.append({
            "type": "designation",
            "carte": carte,
            "contenu": CARTES[carte].get("symbole", ""),
            "remarquables": rem,
        })
        _etat["precedente"] = carte
        _etat["etape"] = "paire"

    elif _etat["etape"] == "paire":
        _symbolique.append({
            "type": "paire",
            "cartes": [_etat["precedente"], carte],
            "contenu": _fetch_paire(_etat["precedente"], carte),
            "remarquables": rem,
        })
        _etat["precedente"] = carte
        _etat["etape"] = "apport"

    elif _etat["etape"] == "apport":
        q = _fetch_qualite(_etat["precedente"], carte)
        _symbolique.append({
            "type": "apport",
            "carte": carte,
            "sur": _etat["precedente"],
            **q,
            "remarquables": rem,
        })
        _etat["precedente"] = carte
        _etat["etape"] = "paire"


def _build_symbolique_resume(context):
    placed = context.get("placed_cards", [])
    reset_symbolique()
    for c in placed:
        traiter_carte(c["value"])

    lignes = []
    for s in _symbolique[-6:]:
        if s["type"] == "designation":
            lignes.append(f"{nom_carte(s['carte'])} : {s['contenu']}")
        elif s["type"] == "paire":
            noms = " / ".join(nom_carte(c) for c in s["cartes"])
            lignes.append(f"{noms} : {s['contenu'][:120]}")
        else:
            lignes.append(
                f"{nom_carte(s['carte'])} sur {nom_carte(s['sur'])} ({s.get('qualite')}) : "
                f"{s.get('texte', '')[:80]} {s.get('conclusion', '')[:80]}"
            )
    return "\n".join(lignes) or "aucun"


# ---------- appel OpenRouter ----------
def interroger_llm(user_text=None, context=None, signal=None, carte_revelee=None):
    if context and "placed_cards" in context:
        resume_sym = _build_symbolique_resume(context)
    else:
        resume_sym = "aucun"

    themes = context.get("memory", {}).get("themes", []) if context else []

    if carte_revelee:
        carte_revelee = dict(carte_revelee)
        carte_revelee["nom"] = nom_carte(carte_revelee.get("valeur"))

    payload = {
        "message_utilisateur": user_text or "",
        "carte_revelee": carte_revelee,
        "resume_symbolique": resume_sym,
        "signal_colonne": signal,
        "themes_precedents": themes,
    }

    user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)

    body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=40,
        )
        resp.raise_for_status()
        data = resp.json()

        msg = data.get("choices", [{}])[0].get("message", {})
        content = msg.get("content")

        if not content:
            print("⚠ LLM a répondu un contenu vide", flush=True)
            return "L'oracle hésite… Reformulez votre intention.", "no", ""

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"Chat": content, "Com": "no", "Theme": ""}

        if not isinstance(parsed, dict):
            parsed = {"Chat": str(parsed), "Com": "no", "Theme": ""}

        chat = str(parsed.get("Chat", "")).strip()
        com = str(parsed.get("Com", "no")).strip().lower()
        theme = str(parsed.get("Theme", "")).strip()

        if com not in ("no", "tx"):
            com = "no"

        return chat, com, theme

    except Exception as e:
        print(f"⚠ Erreur LLM: {e}", flush=True)
        return "L'oracle reste silencieux un instant...", "no", ""
