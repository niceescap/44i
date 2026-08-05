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
    """État symbolique isolé par consultation, cycle de 5 cartes par colonne."""

    STAGES = ["designation", "paire", "apport", "qualite_en_paire", "theme"]

    def __init__(self) -> None:
        self.cards = self._load("52cartes.json", [])
        self.cards_by_code = {item.get("carte"): item for item in self.cards if item.get("carte")}
        self.qualities = self._load("qualites.json", {})
        self.pairs = self._load_pairs()
        # Historique global de la consultation
        self.steps: list[str] = []
        # État du cycle courant (par colonne)
        self._stage_idx = 0
        self.base_card: str | None = None
        self.pair_anchor: tuple[str, str] | None = None
        self.column_cards: list[str] = []

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
            collection = chromadb.PersistentClient(path=path).get_collection(
                os.getenv("SYMBOLIQUE_CHROMA_COLLECTION", "paires")
            )
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
            normalized = [
                f"10{code[-1]}" if self.rank(code) == "10" and code[:-1] == "T" else code
                for code in cards
            ]
            return detecter_remarquables(normalized)
        except Exception as exc:
            print(f"[symbolique] remarquables indisponibles: {exc}", flush=True)
            return []

    def _advance(self) -> None:
        """Passe à l'étape suivante du cycle. Après 'theme', reset pour la colonne suivante."""
        self._stage_idx += 1
        if self._stage_idx >= len(self.STAGES):
            self._stage_idx = 0
            self.base_card = None
            self.pair_anchor = None
            self.column_cards = []

    def propose_theme(self, column_cards: list[str]) -> str:
        """Propose un thème synthétique pour la colonne terminée."""
        if not column_cards:
            return "Colonne vide"
        names = [self.name(c) for c in column_cards]
        symbols = [self.symbol(c) for c in column_cards]
        fragment = " — ".join(s[:60] for s in symbols if s)
        return f"{' / '.join(names)}. {fragment}"

    def process(self, code: str, placed: list[str], column: str, row: int) -> dict:
        code = code.upper()
        self.steps.append(code)
        self.column_cards.append(code)
        stage = self.STAGES[self._stage_idx]
        remarks = self.remarkable(self.steps)
        event: dict = {}

        # ---------- ÉTAPE 1 : Désignation ----------
        if stage == "designation":
            self.base_card = code
            event = {
                "type": "designation",
                "card": code,
                "name": self.name(code),
                "symbol": self.symbol(code),
                "remarkables": remarks,
            }
            self._advance()

        # ---------- ÉTAPE 2 : Symbolique de la paire ----------
        elif stage == "paire":
            if self.base_card is None:
                # Sécurité : changement manuel de colonne sans base
                self.base_card = code
                event = {
                    "type": "designation",
                    "card": code,
                    "name": self.name(code),
                    "symbol": self.symbol(code),
                    "remarkables": remarks,
                }
            else:
                event = {
                    "type": "paire",
                    "cards": [self.base_card, code],
                    "content": self.pair(self.base_card, code),
                    "remarkables": remarks,
                }
                self.pair_anchor = (self.base_card, code)
            self._advance()

        # ---------- ÉTAPE 3 : Qualité + interprétation ----------
        elif stage == "apport":
            # La carte s'apporte à la 2ème carte de la paire (pivot)
            anchor = self.pair_anchor[1] if self.pair_anchor else (self.base_card or code)
            event = {
                "type": "apport",
                "card": code,
                "sur": anchor,
                **self.quality(anchor, code),
                "remarkables": remarks,
            }
            self._advance()

        # ---------- ÉTAPE 4 : Qualité en paire ----------
        elif stage == "qualite_en_paire":
            # La carte 4 apporte sa qualité par rapport à la carte de base (ancrage)
            base = self.base_card or (self.pair_anchor[0] if self.pair_anchor else code)
            event = {
                "type": "qualite_en_paire",
                "card": code,
                "base_card": base,
                "quality_vs_base": self.quality(base, code),
                "pair_context": list(self.pair_anchor) if self.pair_anchor else [],
                "remarkables": remarks,
            }
            self._advance()

        # ---------- ÉTAPE 5 : Thème + cloture automatique ----------
        elif stage == "theme":
            event = {
                "type": "theme",
                "card": code,
                "column_cards": list(self.column_cards),
                "theme_proposal": self.propose_theme(self.column_cards),
                "remarkables": remarks,
            }
            self._advance()

        # ---------- Signaux ----------
        signal = None
        # 5ème carte = cloture automatique et obligatoire de la colonne
        if stage == "theme":
            signal = "obligation:cloture_colonnette_complete"
        elif Counter(self.rank(c) for c in self.steps)["A"] >= 2:
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
