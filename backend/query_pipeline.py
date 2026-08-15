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

RANK_FR = {
    "A": "As",
    "2": "Deux",
    "3": "Trois",
    "4": "Quatre",
    "5": "Cinq",
    "6": "Six",
    "7": "Sept",
    "8": "Huit",
    "9": "Neuf",
    "T": "Dix",
    "J": "Valet",
    "Q": "Dame",
    "K": "Roi",
}
SUIT_FR = {"C": "Trèfle", "H": "Cœur", "D": "Carreau", "S": "Pique"}
COLD_START_LEXIQUE = (
    "C = Trèfle    H = Cœur    D = Carreau    S = Pique\n"
    "A = As    T = 10    J = Valet    Q = Dame    K = Roi"
)


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


def _normalize_code(code: str) -> str:
    """detector_rem attend 10X, pas TX."""
    code = code.upper()
    if len(code) >= 2 and code[:-1] == "T":
        return "10" + code[-1]
    return code


def _detecter(cartes: list[str]) -> list[dict]:
    try:
        from detector_rem import detecter_remarquables
        return detecter_remarquables([_normalize_code(c) for c in cartes])
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

    def designation(self, code: str) -> str:
        return str(self.cartes.get(code, {}).get("symbole", ""))

    def nom_fr(self, code: str) -> str:
        code = (code or "").upper().strip()
        if len(code) < 2:
            return code
        rank, suit = code[:-1], code[-1]
        return f"{RANK_FR.get(rank, rank)} de {SUIT_FR.get(suit, suit)}"

    def etiquette(self, code: str) -> str:
        code = (code or "").upper().strip()
        if not code:
            return ""
        return f"{self.nom_fr(code)} ({code})"

    def nom(self, code: str) -> str:
        item = self.cartes.get(code, {})
        return str(item.get("nom") or item.get("intitule") or self.nom_fr(code))

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

        desig = self.designation(carte)

        if self.etat == "designation":
            self.symbolique.append({
                "carte": carte,
                "nom": self.nom(carte),
                "type": "designation",
                "designation": desig,
                "contenu": desig,
                "remarquables": balises,
            })
            self.carte_paire = carte
            self.carte_courante = carte
            self.etat = "paire"

        elif self.etat == "paire":
            base = self.carte_paire or carte
            sig = self.fetch_paire(base, carte)
            self.symbolique.append({
                "cartes": [base, carte],
                "type": "paire",
                "designation": desig,
                "designations": {
                    base: self.designation(base),
                    carte: desig,
                },
                "contenu": sig,
                "contenu_enrichi": f"{desig} — {sig}",
                "remarquables": balises,
            })
            self.carte_courante = carte
            self.etat = "apport"

        elif self.etat == "apport":
            sur = self.carte_courante or carte
            q = self.fetch_qualite(sur, carte)
            expression = " | ".join(
                part for part in (q["texte"], q["qualite"], q["conclusion"]) if part
            )
            self.symbolique.append({
                "carte": carte,
                "nom": self.nom(carte),
                "type": "apport",
                "sur": sur,
                "designation": desig,
                "texte": q["texte"],
                "qualite": q["qualite"],
                "conclusion": q["conclusion"],
                "contenu_enrichi": f"{desig} — {expression}",
                "remarquables": balises,
            })
            self.carte_paire = carte
            self.carte_courante = carte
            self.etat = "paire"

        return self.snapshot()

    def contexte_llm(self) -> dict[str, Any]:
        """Payload prêt pour le LLM : désignations + paire + apport + remarquables."""
        by_type = {item.get("type"): item for item in self.symbolique}
        remarquables: list[dict] = []
        seen: set[str] = set()
        for item in self.symbolique:
            for balise in item.get("remarquables") or []:
                key = json.dumps(balise, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                remarquables.append(balise)
        return {
            "type": "consultation_3cartes",
            "version": "2",
            "cartes_revelees": list(self.cartes_posees),
            "triple_contexte": {
                "designation": by_type.get("designation"),
                "paire": by_type.get("paire"),
                "apport": by_type.get("apport"),
            },
            "remarquables": remarquables,
        }

    @staticmethod
    def _remarquable_line(balise: dict[str, Any]) -> str:
        extra = balise.get("signification") or balise.get("qualite") or ""
        cards = "+".join(balise.get("cartes") or [])
        line = f"Remarquable {balise.get('sous_type', '')} {cards}".strip()
        if extra:
            line += f" — {extra}"
        return line

    def cold_start_lines(self) -> list[str]:
        """Contrat Prompt.txt pour le LLM. Indépendant de logs() (commentaire UI).

        1 · CODE — désignation
        2 · CODE — désignation
        3 · CODE — désignation
        Paire A+B — désignation 2e + signification
        Apport C sur B — désignation 3e + qualité / conclusion
        Remarquable …
        """
        codes = list(self.cartes_posees)
        if not codes:
            for item in self.symbolique:
                kind = item.get("type")
                if kind == "designation" and item.get("carte"):
                    codes.append(str(item["carte"]))
                elif kind == "paire":
                    cartes = item.get("cartes") or []
                    if cartes:
                        codes.append(str(cartes[-1]))
                elif kind == "apport" and item.get("carte"):
                    codes.append(str(item["carte"]))

        lines: list[str] = []
        for n, code in enumerate(codes, 1):
            lines.append(f"{n} · {code} — {self.designation(code)}")

        for item in self.symbolique:
            kind = item.get("type")
            if kind == "paire":
                cartes = "+".join(item.get("cartes") or [])
                desig = item.get("designation") or ""
                sig = item.get("contenu") or ""
                if desig and sig:
                    lines.append(f"Paire {cartes} — {desig} — {sig}")
                else:
                    lines.append(
                        f"Paire {cartes} — {item.get('contenu_enrichi') or sig or desig}"
                    )
            elif kind == "apport":
                desig = item.get("designation") or ""
                expression = " | ".join(
                    part
                    for part in (item.get("texte"), item.get("qualite"), item.get("conclusion"))
                    if part
                )
                payload = (
                    f"{desig} — {expression}"
                    if desig and expression
                    else (item.get("contenu_enrichi") or item.get("conclusion") or desig)
                )
                lines.append(
                    f"Apport {item.get('carte')} sur {item.get('sur')} — {payload}"
                )

        seen: set[str] = set()
        for item in self.symbolique:
            for balise in item.get("remarquables") or []:
                key = json.dumps(balise, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(self._remarquable_line(balise))
        return lines

    def logs(self) -> list[str]:
        """Commentaire de plateau pour l'UI. Ne pas envoyer au LLM."""
        lines: list[str] = []
        n = 0
        seen: set[str] = set()
        for item in self.symbolique:
            kind = item.get("type")
            if kind == "designation":
                n += 1
                lines.append(
                    f"{n} · {item.get('carte')} — {item.get('designation') or item.get('contenu') or ''}"
                )
            elif kind == "paire":
                cartes = "+".join(item.get("cartes") or [])
                lines.append(
                    f"Paire {cartes} — {item.get('contenu_enrichi') or item.get('contenu') or ''}"
                )
            elif kind == "apport":
                lines.append(
                    f"Apport {item.get('carte')} sur {item.get('sur')} — "
                    f"{item.get('contenu_enrichi') or item.get('conclusion') or ''}"
                )
            for balise in item.get("remarquables") or []:
                key = json.dumps(balise, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(self._remarquable_line(balise))
        return lines

    def snapshot(self) -> dict[str, Any]:
        return {
            "symbolique": list(self.symbolique),
            "etat": self.etat,
            "cartes_posees": list(self.cartes_posees),
            "logs": self.logs(),
            "contexte_llm": self.contexte_llm(),
        }
