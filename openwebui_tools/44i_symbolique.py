"""Outil OpenWebUI read-only pour la symbolique de 44 interprètes.

À coller/importer dans OpenWebUI comme outil Python custom.
Les chemins sont configurables par variables d'environnement :
- SYMBOLIQUE_EXTRACTOR_DIR (défaut: /data/44i/extractor)
- SYMBOLIQUE_CHROMA_DIR (défaut: /data/44i/chroma_db)
- SYMBOLIQUE_CHROMA_COLLECTION (défaut: paires)

L'outil ne modifie jamais une session, un deck, un historique ou un fichier.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import Field

try:
    import chromadb
except ImportError:  # permet au reste de l'outil de fonctionner sans ChromaDB
    chromadb = None


CODE_RE = re.compile(r"^(?:T|[A2-9JQK])[CDHS]$", re.IGNORECASE)


class Tools:
    """Recherche symbolique strictement en lecture seule."""

    def __init__(self):
        self.extractor_dir = Path(
            os.getenv("SYMBOLIQUE_EXTRACTOR_DIR", "/data/44i/extractor")
        )
        self.chroma_dir = Path(
            os.getenv("SYMBOLIQUE_CHROMA_DIR", "/data/44i/chroma_db")
        )
        self.collection_name = os.getenv("SYMBOLIQUE_CHROMA_COLLECTION", "paires")
        self.cards = self._load_json("52cartes.json", [])
        self.cards_by_code = {
            item.get("carte", "").upper(): item
            for item in self.cards
            if isinstance(item, dict) and item.get("carte")
        }
        self.qualities = self._load_json("qualites.json", {})
        self._pair_collection = self._load_pair_collection()

    def _load_json(self, filename: str, default: Any) -> Any:
        try:
            with (self.extractor_dir / filename).open(encoding="utf-8") as stream:
                return json.load(stream)
        except (OSError, json.JSONDecodeError):
            return default

    def _load_pair_collection(self):
        if chromadb is None or not self.chroma_dir.exists():
            return None
        try:
            client = chromadb.PersistentClient(path=str(self.chroma_dir))
            return client.get_collection(self.collection_name)
        except Exception as exc:
            print(f"[44i] ChromaDB indisponible: {exc}", flush=True)
            return None

    @staticmethod
    def _code(value: str) -> str:
        return value.strip().upper()

    @classmethod
    def _valid_code(cls, value: str) -> bool:
        return bool(CODE_RE.fullmatch(cls._code(value)))

    @staticmethod
    def _json(data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _card_result(self, code: str) -> dict[str, Any]:
        code = self._code(code)
        item = self.cards_by_code.get(code)
        if not item:
            return {"code": code, "found": False, "source": "52cartes.json"}

        public_item = {
            key: value
            for key, value in item.items()
            if not str(key).startswith("_")
        }
        return {
            "code": code,
            "found": True,
            "source": "52cartes.json",
            "card": public_item,
        }

    def rechercher_carte(
        self,
        code: str = Field(
            ...,
            description="Code de carte, par exemple QC, 8H ou 10S.",
        ),
    ) -> str:
        """Recherche la désignation symbolique d'une carte dans 52cartes.json."""
        code = self._code(code)
        if not self._valid_code(code):
            return self._json({"error": "Code de carte invalide", "code": code})
        return self._json(self._card_result(code))

    def rechercher_paire(
        self,
        carte_a: str = Field(..., description="Premier code de carte."),
        carte_b: str = Field(..., description="Second code de carte."),
    ) -> str:
        """Recherche la relation symbolique entre deux cartes dans ChromaDB."""
        first = self._code(carte_a)
        second = self._code(carte_b)
        if not self._valid_code(first) or not self._valid_code(second):
            return self._json({"error": "Code de carte invalide", "cards": [first, second]})

        pair_id = "|".join(sorted([first, second]))
        document = None
        metadata = None
        if self._pair_collection is not None:
            try:
                result = self._pair_collection.get(
                    ids=[pair_id], include=["documents", "metadatas"]
                )
                documents = result.get("documents") or []
                metadatas = result.get("metadatas") or []
                document = documents[0] if documents else None
                metadata = metadatas[0] if metadatas else None
            except Exception as exc:
                print(f"[44i] Recherche paire impossible: {exc}", flush=True)

        return self._json(
            {
                "cards": [first, second],
                "found": bool(document),
                "pair_id": pair_id,
                "content": document or "",
                "metadata": metadata or {},
                "source": "chromadb",
            }
        )

    def rechercher_qualite(
        self,
        carte_base: str = Field(..., description="Carte qui reçoit l'apport."),
        carte_apport: str = Field(..., description="Carte apportée à la carte de base."),
    ) -> str:
        """Recherche la qualité harmonie/conflit entre deux cartes."""
        base = self._code(carte_base)
        apport = self._code(carte_apport)
        if not self._valid_code(base) or not self._valid_code(apport):
            return self._json({"error": "Code de carte invalide", "cards": [base, apport]})

        key = f"{base}|{apport[-1]}"
        quality = self.qualities.get(key, {})
        result = {
            "cards": [base, apport],
            "found": bool(quality),
            "quality_id": key,
            "quality": quality,
            "source": "qualites.json",
        }
        return self._json(result)

    def rechercher_remarquables(
        self,
        cartes: str = Field(
            ...,
            description="Codes de cartes séparés par des virgules, par exemple AC,AH,8C.",
        ),
    ) -> str:
        """Recherche les configurations remarquables d'une liste de cartes."""
        values = [self._code(value) for value in cartes.split(",") if value.strip()]
        invalid = [value for value in values if not self._valid_code(value)]
        if invalid:
            return self._json({"error": "Code de carte invalide", "invalid": invalid})

        try:
            extractor_path = str(self.extractor_dir)
            if extractor_path not in sys.path:
                sys.path.insert(0, extractor_path)
            from detector_rem import detecter_remarquables
            remarkable = detecter_remarquables(values)
        except Exception as exc:
            print(f"[44i] Détection remarquable indisponible: {exc}", flush=True)
            remarkable = []

        return self._json(
            {
                "cards": values,
                "remarkables": remarkable,
                "source": "detector_rem.py",
            }
        )
