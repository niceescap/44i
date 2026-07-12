#!/usr/bin/env python3
"""
randomizer_52.py — Gestion d'un deck de 52 cartes mélangées.
Utilisé par croupier.py pour le tirage aléatoire.
"""

import json
import random
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARTES_FILE = os.path.join(BASE_DIR, "..", "extractor", "52cartes.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "deck_shuffled.json")


def generer_deck():
    valeurs = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    couleurs = ["C", "D", "H", "S"]
    deck = [v + c for c in couleurs for v in valeurs]
    random.shuffle(deck)
    return deck


def sauvegarder_deck(deck):
    data = {
        "deck": deck,
        "remaining": len(deck),
        "drawn": 0,
    }
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def tirer_carte():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = sauvegarder_deck(generer_deck())

    if not data["deck"]:
        print("⚠ Deck épuisé ! Régénération...", flush=True)
        data = sauvegarder_deck(generer_deck())

    carte = data["deck"].pop(0)
    data["drawn"] += 1
    data["remaining"] = len(data["deck"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return carte


def reset_deck():
    return sauvegarder_deck(generer_deck())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_deck()
        print("Deck réinitialisé")
    elif len(sys.argv) > 1 and sys.argv[1] == "draw":
        print(tirer_carte())
    else:
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"Deck actuel : {data['remaining']} cartes restantes")
        except FileNotFoundError:
            reset_deck()
            print("Deck initialisé")
