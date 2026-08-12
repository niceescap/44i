#!/usr/bin/env python3
"""Pipeline symbolique 3 étapes — port de testeur_query.py.

désignation → paire → apport. Aucun LLM. Aucune écriture disque.
Ressources : extractor/52cartes.json, qualites.json, chroma_db/paires,
extractor/detector_rem.detecter_remarquables.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "extractor"

if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))


def _load_json(name: str, default):
    path = EXTRACTOR / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _load_cartes() -> dict[str, dict]:
    data = _load_json("52cartes.json", [])
    return {c["carte"]: c for c in data if isinstance(c, dict) and c.get("carte")}


def _load_paires():
    try:
        import chromadb
    except ImportError:
        print("[query] chromadb absent", flush=True)
        return None
    candidates = [
        Path(os.getenv("SYMBOLIQUE_CHROMA_DIR", "")) if os.getenv("SYMBOLIQUE_CHROMA_DIR") else None,
        ROOT / "chroma_db",
        EXTRACTOR / "chroma_db",
    ]
    path = next((p for p in candidates if p and p.exists()), None)
    if path is None:
        print("[query] chroma_db introuvable (essayé ~/44i/chroma_db et extractor/chroma_db)", flush=True)
        return None
    try:
        client = chromadb.PersistentClient(path=str(path))
        return client.get_collection("paires")
    except Exception as exc:
        print(f"[query] collection paires indisponible: {exc}", flush=True)
        return None


def _detecter(cartes: list[str]) -> list[dict]:
    try:
        from detector_rem import detecter_remarquables
        return detecter_remarquables(cartes)
    except Exception as exc:
        print(f"[query] remarquables indisponibles: {exc}", flush=True)
        return []


_CARTES: dict | None = None
_QUALITES = None
_PAIRES = None
_PAIRES_READY = False


def _shared_cartes() -> dict:
    global _CARTES
    if _CARTES is None:
        _CARTES = _load_cartes()
    return _CARTES


def _shared_qualites():
    global _QUALITES
    if _QUALITES is None:
        _QUALITES = _load_json("qualites.json", {})
    return _QUALITES


def _shared_paires():
    global _PAIRES, _PAIRES_READY
    if not _PAIRES_READY:
        _PAIRES = _load_paires()
        _PAIRES_READY = True
    return _PAIRES


class QueryPipeline:
    """État designation → paire → apport, stoppable à 3 cartes."""

    def __init__(self) -> None:
        self.cartes = _shared_cartes()
        self.qualites = _shared_qualites()
        self.col_paires = _shared_paires()
        self.reset()

    def reset(self) -> None:
        self.symbolique: list[dict[str, Any]] = []
        self.etat = "designation"
        self.carte_paire: str | None = None
        self.carte_courante: str | None = None
        self.cartes_posees: list[str] = []

    def fetch_paire(self, c1: str, c2: str) -> str:
        if not self.col_paires:
            return "(paire non trouvée)"
        pair_id = "|".join(sorted([c1, c2]))
        try:
            result = self.col_paires.get(ids=[pair_id], include=["documents"])
            docs = result.get("documents") or []
            if docs:
                return docs[0]
        except Exception:
            pass
        return "(paire non trouvée)"

    def fetch_qualite(self, carte_base: str, carte_apport: str) -> dict[str, str]:
        cle = f"{carte_base}|{carte_apport[-1]}"
        q_data = self.qualites.get(cle, {}) if isinstance(self.qualites, dict) else {}
        texte = q_data.get("texte", "")
        qualite = q_data.get("qualite", "indefini")
        carte_def = self.cartes.get(carte_apport, {})
        conclusion = carte_def.get(qualite, "") if qualite in ("harmonie", "conflit") else ""
        return {"texte": texte, "qualite": qualite, "conclusion": conclusion}

    def traiter(self, carte: str) -> dict[str, Any]:
        carte = carte.upper().strip()
        if carte not in self.cartes:
            raise ValueError(f"Carte inconnue : {carte}")

        self.cartes_posees.append(carte)
        balises = _detecter(self.cartes_posees)

        if self.etat == "designation":
            carte_def = self.cartes[carte]
            self.symbolique.append({
                "carte": carte,
                "type": "designation",
                "contenu": carte_def.get("symbole", ""),
                "remarquables": balises,
            })
            self.carte_paire = carte
            self.carte_courante = carte
            self.etat = "paire"

        elif self.etat == "paire":
            sig = self.fetch_paire(self.carte_paire or carte, carte)
            self.symbolique.append({
                "cartes": [self.carte_paire, carte],
                "type": "paire",
                "contenu": sig,
                "remarquables": balises,
            })
            self.carte_courante = carte
            self.etat = "apport"

        elif self.etat == "apport":
            q = self.fetch_qualite(self.carte_courante or carte, carte)
            self.symbolique.append({
                "carte": carte,
                "type": "apport",
                "sur": self.carte_courante,
                "texte": q["texte"],
                "qualite": q["qualite"],
                "conclusion": q["conclusion"],
                "remarquables": balises,
            })
            self.carte_paire = carte
            self.carte_courante = carte
            self.etat = "paire"

        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "symbolique": list(self.symbolique),
            "etat": self.etat,
            "cartes_posees": list(self.cartes_posees),
        }
