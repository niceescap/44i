#!/usr/bin/env python3
"""
Qualifier — Dame de Trèfle
Lit couleurs.json, envoie chaque texte à Qwen pour classification,
stocke le résultat dans qualites.json.

208 combinaisons : 52 cartes × 4 couleurs
Sortie : qualites.json { "6D|C": {"texte": "...", "qualite": "harmonie"}, ... }
"""

import json
import time
import requests

# ---------- CONFIGURATION ----------
OLLAMA_URL    = "http://localhost:11434/api/generate"
LLM_MODEL     = "qwen2.5:3b"
COULEURS_FILE = "couleurs.json"
OUTPUT_FILE   = "qualites.json"

COULEUR_CODE = {
    "trefle":  "C",
    "coeur":   "H",
    "carreau": "D",
    "pique":   "S",
}

# ---------- PROMPT ----------
PROMPT_TEMPLATE = """Classifie ce texte en une seule catégorie.

Texte : "{texte}"

- harmonie : paix, amour, amitié, confiance, solution, énergie positive
- conflit : guerre, rivalité, jalousie, anxiété, problème, menace

Réponds uniquement par : harmonie ou conflit"""

# ---------- APPEL QWEN ----------
def classify(texte: str, retries: int = 3) -> str:
    prompt = PROMPT_TEMPLATE.format(texte=texte)
    for attempt in range(retries):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model":  LLM_MODEL,
                "prompt": prompt,
                "stream": False
            }, timeout=120)  # 60s au lieu de 30s
            resp.raise_for_status()
            reponse = resp.json()["response"].strip().lower()
            if "harmonie" in reponse:
                return "harmonie"
            elif "conflit" in reponse:
                return "conflit"
            else:
                return "indefini"
        except Exception as e:
            print(f"\n  ⚠️  Tentative {attempt+1}/{retries} échouée : {e}")
            time.sleep(2)
    return "indefini"

# ---------- MAIN ----------
def main():
    with open(COULEURS_FILE, encoding="utf-8") as f:
        couleurs = json.load(f)

    qualites = {}
    total    = len(couleurs) * 4
    count    = 0

    print(f"=== Qualification de {total} associations ===\n")

    for entry in couleurs:
        carte = entry["carte"]
        for cle, suffixe in COULEUR_CODE.items():
            texte = entry.get(cle, "")
            if not texte:
                continue

            key   = f"{carte}|{suffixe}"
            count += 1

            print(f"[{count}/{total}] {key} → \"{texte}\" ... ", end="", flush=True)
            qualite = classify(texte)
            print(qualite)

            qualites[key] = {
                "texte":   texte,
                "qualite": qualite
            }

            time.sleep(0.1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(qualites, f, ensure_ascii=False, indent=2)

    indefinis = [k for k, v in qualites.items() if v["qualite"] == "indefini"]
    print(f"\n✅ {len(qualites)} qualités sauvegardées dans {OUTPUT_FILE}")
    if indefinis:
        print(f"⚠️  {len(indefinis)} non classifiés : {indefinis}")

if __name__ == "__main__":
    main()
