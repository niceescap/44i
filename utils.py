#!/usr/bin/env python3
"""
utils.py — Fonctions partagées entre app.py et chatbox.py
Évite les imports circulaires.
"""

import json
import os
import subprocess
import sys
import threading
from datetime import datetime

from llm_handler import reset_symbolique

PIPELINES_DIR = os.path.dirname(os.path.abspath(__file__))

dealer_lock = threading.Lock()
dealer = None  # initialisé par app.py via set_dealer()


def set_dealer(dealer_instance):
    global dealer
    dealer = dealer_instance


def run_renderer():
    try:
        subprocess.run(
            [sys.executable, "tapis.py"],
            cwd=PIPELINES_DIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[renderer] {e}", flush=True)


def write_chatin(text):
    with open("chatin.json", "w", encoding="utf-8") as f:
        json.dump(
            {"role": "llm", "text": text, "ts": datetime.now().isoformat()},
            f,
            ensure_ascii=False,
            indent=2,
        )


def empty_chatin():
    try:
        if os.path.exists("chatin.json"):
            os.remove("chatin.json")
    except OSError:
        pass


def build_context():
    placed = [
        {"slot": o["slot"], "value": o["value"]}
        for o in dealer.state.get("objects", [])
        if o.get("type") == "card" and o.get("face") == "up" and o.get("value")
    ]
    return {
        "state": dict(dealer.state),
        "memory": dict(dealer.memory),
        "placed_cards": placed,
    }


def run_cmd(cmd):
    if cmd == "init":
        dealer.init()
        reset_symbolique()
        empty_chatin()
        return True
    if cmd == "start":
        dealer.start()
        reset_symbolique()
        return True
    if cmd == "restart":
        return dealer.restart()
    return dealer.execute(cmd)


def executer_commande(commande, theme=""):
    """
    Exécute une commande LLM : "no" (rien) ou "tx" (colonne suivante).
    """
    global dealer
    if dealer is None:
        print("[utils] dealer non initialisé", flush=True)
        return

    if not commande or commande.lower() == "no":
        return

    if commande.lower() == "tx":
        with dealer_lock:
            old_col = dealer.memory["active_col"]
            change = dealer.change_column("tx")
            if change:
                if theme:
                    dealer.memory.setdefault("themes", []).append({
                        "colonne": old_col,
                        "theme": theme,
                    })
                dealer.save()
        if change:
            run_renderer()
    else:
        print(f"[exec] commande ignorée: {commande}", flush=True)
