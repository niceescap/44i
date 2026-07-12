from __future__ import annotations

import json
import os
from pathlib import Path

try:
    import chromadb
except ImportError:
    chromadb = None

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "extractor"

RANKS = {"A": "As", "K": "Roi", "Q": "Dame", "J": "Valet", "10": "Dix", "9": "Neuf", "8": "Huit", "7": "Sept", "6": "Six", "5": "Cinq", "4": "Quatre", "3": "Trois", "2": "Deux"}
SUITS = {"C": "Trèfle", "D": "Carreau", "H": "Cœur", "S": "Pique"}


def load(name: str, default):
    try:
        return json.loads((EXTRACTOR / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


_raw_cards = load("52cartes.json", [])
CARDS = {item.get("carte"): item for item in _raw_cards if item.get("carte")}
QUALITIES = load("qualites.json", {})


def card_name(code: str) -> str:
    code = code.upper()
    meta = CARDS.get(code, {})
    return meta.get("nom") or meta.get("intitule") or f"{RANKS.get(code[:-1], code[:-1])} de {SUITS.get(code[-1], code[-1])}"


def card_symbol(code: str) -> str:
    return str(CARDS.get(code, {}).get("symbole", ""))


def card_info(code: str) -> dict[str, str]:
    return {"name": card_name(code), "symbol": card_symbol(code)}


def interpretation(codes: list[str]) -> str:
    lines: list[str] = []
    for code in codes:
        info = card_info(code)
        lines.append(f"{info['name']} : {info['symbol'] or 'Carte à interpréter symboliquement.'}")
    return "\n".join(lines)
