from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import os

try:
    import chromadb
except ImportError:
    chromadb = None

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "extractor"


class SymbolicEngine:
    """État symbolique isolé par consultation, dérivé de via."""

    def __init__(self) -> None:
        self.cards = self._load("52cartes.json", [])
        self.cards_by_code = {item.get("carte"): item for item in self.cards if item.get("carte")}
        self.qualities = self._load("qualites.json", {})
        self.steps: list[dict] = []
        self.previous: str | None = None
        self.stage = "designation"
        self.pairs = self._load_pairs()

    @staticmethod
    def _load(name: str, default):
        try:
            return json.loads((EXTRACTOR / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def _load_pairs(self):
        path = os.getenv("SYMBOLIQUE_CHROMA_DIR", str(ROOT / "chroma_db"))
        if chromadb is None or not Path(path).exists():
            return None
        try:
            collection = chromadb.PersistentClient(path=path).get_collection(os.getenv("SYMBOLIQUE_CHROMA_COLLECTION", "paires"))
            print(f"[symbolique] ChromaDB chargée pour session: {path}", flush=True)
            return collection
        except Exception as exc:
            print(f"[symbolique] ChromaDB session indisponible: {exc}", flush=True)
            return None

    @staticmethod
    def rank(code: str) -> str:
        value = code[:-1].upper()
        return "10" if value == "T" else value

    def name(self, code: str) -> str:
        code = code.upper()
        item = self.cards_by_code.get(code, {})
        return item.get("nom") or item.get("intitule") or code

    def symbol(self, code: str) -> str:
        return str(self.cards_by_code.get(code.upper(), {}).get("symbole", ""))

    def pair(self, first: str, second: str) -> str:
        if not self.pairs:
            return ""
        pair_id = "|".join(sorted([first, second]))
        try:
            result = self.pairs.get(ids=[pair_id], include=["documents"])
            documents = result.get("documents") or []
            return documents[0] if documents else ""
        except Exception as exc:
            print(f"[symbolique] paire indisponible: {exc}", flush=True)
            return ""

    def quality(self, base: str, apport: str) -> dict:
        key = f"{base}|{apport[-1]}"
        item = self.qualities.get(key, {})
        card = self.cards_by_code.get(apport, {})
        kind = item.get("qualite", "indefini")
        return {
            "texte": item.get("texte", ""),
            "qualite": kind,
            "conclusion": card.get(kind, "") if kind in {"harmonie", "conflit"} else "",
        }

    def remarkable(self, cards: list[str]) -> list[dict]:
        """Réutilise le détecteur validé, avec normalisation T -> 10."""
        try:
            import sys
            if str(EXTRACTOR) not in sys.path:
                sys.path.insert(0, str(EXTRACTOR))
            from detector_rem import detecter_remarquables
            normalized = [f"10{code[-1]}" if self.rank(code) == "10" and code[:-1] == "T" else code for code in cards]
            return detecter_remarquables(normalized)
        except Exception as exc:
            print(f"[symbolique] remarquables indisponibles: {exc}", flush=True)
            return []

    def process(self, code: str, placed: list[str], column: str, row: int) -> dict:
        code = code.upper()
        self.steps.append(code)
        remarks = self.remarkable(self.steps)
        event: dict = {"type": "designation", "card": code, "name": self.name(code), "symbol": self.symbol(code), "remarkables": remarks}
        if self.stage == "paire" and self.previous:
            event = {"type": "paire", "cards": [self.previous, code], "content": self.pair(self.previous, code), "remarkables": remarks}
            self.stage = "apport"
        elif self.stage == "apport" and self.previous:
            event = {"type": "apport", "card": code, "sur": self.previous, **self.quality(self.previous, code), "remarkables": remarks}
            self.stage = "paire"
        else:
            self.stage = "paire"
        self.previous = code
        signal = None
        if Counter(self.rank(c) for c in self.steps)["A"] >= 2:
            signal = "obligation:cloture_deuxieme_as"
        elif row >= 11:
            signal = "obligation:cloture_immediate"
        elif row >= 5:
            signal = "conseil:cloture_bientot"
        return {"event": event, "signal": signal, "summary": self.summary()}

    def summary(self) -> str:
        lines = []
        for step in self.steps[-6:]:
            lines.append(f"{self.name(step)} : {self.symbol(step)}")
        return "\n".join(lines) or "aucun"
