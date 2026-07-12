#!/usr/bin/env python3
"""
croupier.py — Dame de Trèfle
Logique de tirage locale.
A1 = deck, B1-H1 = ligne de 7, A2-E12 = 5 colonnes.
"""

import json
import os
import re
from randomizer import tirer_carte, reset_deck


class Dealer:

    DECK_SLOT = "A1"
    TOP_SLOTS = ["B1", "C1", "D1", "E1", "F1", "G1", "H1"]
    DRAW_COLS = ["A", "B", "C", "D", "E"]
    DRAW_ROWS = list(range(2, 13))   # 11 cartes max par colonne
    HARD_LIMIT = 11
    SOFT_LIMIT = 5

    def __init__(self):
        self.memory = {
            "status": "idle",
            "phase": "init",
            "deck_size": 52,
            "deck_remaining": 52,
            "tirage_sept": 0,
            "active_col": "A",
            "column_signal": None,
            "themes": [],
            "last_action": "",
        }
        self.state = {
            "board": {"cols": 8, "rows": 12},
            "objects": [
                {"id": "deck", "type": "stack", "slot": self.DECK_SLOT, "face": "down"}
            ],
        }
        self._next_card_id = 1
        self._cartes = self._load_cartes()

    def _load_cartes(self):
        path = os.path.join(os.path.dirname(__file__), "..", "extractor", "52cartes.json")
        try:
            with open(path, encoding="utf-8") as f:
                return {c["carte"]: c for c in json.load(f)}
        except Exception:
            return {}

    def _new_card(self, slot, face, value=None):
        obj = {
            "id": f"card_{self._next_card_id}",
            "type": "card",
            "slot": slot,
            "face": face,
        }
        if value is not None:
            obj["value"] = value
        self._next_card_id += 1
        return obj

    def _find_card(self, slot, face=None):
        for obj in self.state["objects"]:
            if obj.get("slot") != slot or obj.get("type") != "card":
                continue
            if face is not None and obj.get("face") != face:
                continue
            return obj
        return None

    def _count_col(self, col):
        return sum(
            1 for o in self.state["objects"]
            if o.get("type") == "card" and o.get("slot", "").startswith(col)
            and o.get("slot") != self.DECK_SLOT
        )

    def _top_count(self):
        return sum(1 for s in self.TOP_SLOTS if self._find_card(s))

    def get_column_signal(self):
        col = self.memory["active_col"]
        count = self._count_col(col)
        if count >= self.HARD_LIMIT:
            return "obligation:cloture_immediate"
        if count >= self.SOFT_LIMIT:
            return "conseil:cloture_bientot"
        return None

    def get_card_designation(self, card_value):
        return self._cartes.get(card_value, {}).get("symbole", "")

    # ---------- commandes principales ----------

    def init(self):
        self.memory.update({
            "status": "initialized",
            "phase": "init",
            "deck_remaining": 52,
            "tirage_sept": 0,
            "active_col": "A",
            "column_signal": None,
            "themes": [],
            "last_action": "Plateau initialisé",
        })
        self._next_card_id = 1
        self.state["objects"] = [
            {"id": "deck", "type": "stack", "slot": self.DECK_SLOT, "face": "down"}
        ]
        return True

    def start(self):
        reset_deck()
        self._next_card_id = 1
        objects = [
            {"id": "deck", "type": "stack", "slot": self.DECK_SLOT, "face": "down"}
        ]
        for slot in self.TOP_SLOTS:
            valeur = tirer_carte()
            objects.append(self._new_card(slot, face="down", value=valeur))

        self.memory.update({
            "status": "started",
            "phase": "start",
            "deck_remaining": self.memory["deck_size"] - len(self.TOP_SLOTS),
            "tirage_sept": len(self.TOP_SLOTS),
            "active_col": "A",
            "column_signal": None,
            "themes": [],
            "last_action": "7 cartes en B1-H1",
        })
        self.state["objects"] = objects
        return True

    def restart(self):
        if self.memory["deck_remaining"] <= 0:
            self.memory["last_action"] = "Deck épuisé"
            return False

        added = 0
        for slot in self.TOP_SLOTS:
            if self._find_card(slot):
                continue
            if self.memory["deck_remaining"] <= 0:
                break
            valeur = tirer_carte()
            self.state["objects"].append(self._new_card(slot, face="down", value=valeur))
            self.memory["deck_remaining"] -= 1
            added += 1

        if added == 0:
            return False

        self.memory["tirage_sept"] += added
        self.memory["phase"] = "restart"
        self.memory["last_action"] = f"Redistribution de {added} cartes"
        return True

    def place_clicked_card(self, slot_source):
        """
        Place la carte cliquée dans la colonne active.
        Force le passage de colonne si la colonne active est pleine.
        Redistribue automatiquement la ligne si elle est vide.
        """
        if slot_source not in self.TOP_SLOTS:
            return None
        card = self._find_card(slot_source, face="down")
        if not card:
            return None

        # Si la colonne active est pleine, on force la suivante
        while self._count_col(self.memory["active_col"]) >= self.HARD_LIMIT:
            next_col = self._next_available_col()
            if next_col is None:
                return None
            self.memory["active_col"] = next_col

        col = self.memory["active_col"]
        row = self._count_col(col) + 2
        target = f"{col}{row}"

        card["slot"] = target
        card["face"] = "up"

        self.memory["tirage_sept"] = max(self.memory["tirage_sept"] - 1, 0)
        self.memory["deck_remaining"] = max(self.memory["deck_remaining"] - 1, 0)
        self.memory["phase"] = f"place {target}"
        self.memory["last_action"] = f"{card['value']} → {target}"

        if self._top_count() == 0:
            self.restart()

        return {
            "card": card["value"],
            "designation": self.get_card_designation(card["value"]),
            "from": slot_source,
            "to": target,
            "column_signal": self.get_column_signal(),
        }

    def change_column(self, cmd):
        """
        'tx' -> colonne suivante disponible.
        Une lettre -> colonne demandée.
        """
        if cmd == "tx":
            target = self._next_available_col()
        elif cmd in self.DRAW_COLS:
            target = cmd
        else:
            return None

        if target is None:
            return None
        if self._count_col(target) >= self.HARD_LIMIT:
            return None

        old = self.memory["active_col"]
        if target == old:
            return None

        self.memory["active_col"] = target
        self.memory["phase"] = f"colonne {target}"
        self.memory["last_action"] = f"Passage {old} → {target}"
        self.memory["column_signal"] = self.get_column_signal()
        return {"from": old, "to": target}

    def _next_available_col(self):
        idx = self.DRAW_COLS.index(self.memory["active_col"])
        for i in range(idx + 1, len(self.DRAW_COLS)):
            if self._count_col(self.DRAW_COLS[i]) < self.HARD_LIMIT:
                return self.DRAW_COLS[i]
        return None

    # ---------- persistence ----------

    def save(self):
        with open("state.json", "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        with open("memory.json", "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def execute(self, cmd):
        cmd = cmd.lower().strip()
        if cmd == "init":
            return self.init()
        if cmd == "start":
            return self.start()
        if cmd == "restart":
            return self.restart()
        if cmd in ("tx",) or cmd in self.DRAW_COLS:
            return bool(self.change_column(cmd))
        return False


# ---------- CLI ----------
def main():
    dealer = Dealer()
    print("Commandes : init | start | restart | tx | exit")
    while True:
        raw = input("> ").strip()
        if raw == "exit":
            break
        dealer.execute(raw)
        dealer.save()


if __name__ == "__main__":
    main()
