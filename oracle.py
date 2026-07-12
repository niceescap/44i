#!/usr/bin/env python3
"""
oracle.py — Dame de Trèfle (version unifiée)
Serveur web + bootstrap + supervision dans un seul processus.
"""

import json
import os
import sys
import time
import signal
import threading
import requests
from flask import Flask, request, jsonify, send_from_directory

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
PIPELINES_DIR = BASE_DIR  # On est déjà dans pipelines/
KEY_FILE      = os.path.join(PIPELINES_DIR, "OR_key.txt")
MODEL_FILE    = os.path.join(PIPELINES_DIR, "OR_model.txt")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
HOST = "0.0.0.0"
PORT = 3252

# --------------------------------------------------
# FLASK APP
# --------------------------------------------------
from croupier import Dealer
from chatbox import chat_bp
from llm_handler import interroger_llm
import utils

app = Flask(__name__, static_folder=".", static_url_path="")
app.register_blueprint(chat_bp)

utils.dealer = Dealer()
utils.set_dealer(utils.dealer)
dealer = utils.dealer

RESET = "\033[0m"
GREEN = "\033[32m"

# --------------------------------------------------
# ROUTES FLASK (identiques à l'ancien app.py)
# --------------------------------------------------
@app.route("/")
def index():
    with utils.dealer_lock:
        if dealer.memory["status"] == "idle":
            utils.run_cmd("init")
            utils.run_cmd("start")
            dealer.save()
            utils.run_renderer()
        utils.empty_chatin()
    return send_from_directory(".", "interface.html")


@app.route("/command", methods=["POST"])
def handle_command():
    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd", "").strip().lower()

    with utils.dealer_lock:
        ok = utils.run_cmd(cmd)
        if ok:
            dealer.save()

    if ok:
        utils.run_renderer()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": f"commande invalide: {cmd}"}), 400


@app.route("/state")
def get_state():
    if not os.path.exists("state.json") or not os.path.exists("memory.json"):
        return jsonify({"status": "error", "message": "not ready"}), 503

    try:
        with open("state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        with open("memory.json", "r", encoding="utf-8") as f:
            memory = json.load(f)
        return jsonify({"state": state, "memory": memory})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/masterout", methods=["POST"])
def handle_masterout():
    data = request.get_json(silent=True) or {}
    reponse = data.get("reponse", "").strip()
    parts = reponse.split("|", 1)
    texte = parts[0].strip()

    utils.write_chatin(texte)
    utils.executer_commande("no")
    return jsonify({"status": "ok", "texte": texte, "commande": "no"})


@app.route("/reveal", methods=["POST"])
def handle_reveal():
    data = request.get_json(silent=True) or {}
    source = data.get("slot", "").strip()

    with utils.dealer_lock:
        result = dealer.place_clicked_card(source)
        if not result:
            return jsonify({"status": "error", "message": "Clic invalide ou colonne pleine"}), 400
        dealer.save()

    utils.run_renderer()

    ctx = utils.build_context()
    signal = result.get("column_signal")

    carte_revelee = {
        "valeur": result["card"],
        "designation": result["designation"],
        "emplacement": result["to"],
    }

    chat_text, commande, theme = interroger_llm(
        user_text=None,
        context=ctx,
        signal=signal,
        carte_revelee=carte_revelee,
    )

    utils.executer_commande(commande, theme=theme)
    utils.write_chatin(chat_text)

    return jsonify({
        "status": "ok",
        "moved": result,
        "chat": chat_text,
        "commande": commande,
    })


# --------------------------------------------------
# BOOTSTRAP & SUPERVISION
# --------------------------------------------------
def liberer_port(port):
    """Tue les processus qui occupent le port."""
    try:
        import subprocess
        res = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        for pid in res.stdout.strip().split():
            os.kill(int(pid), signal.SIGKILL)
            print(f"  🧹 processus {pid} sur :{port} tué", flush=True)
    except Exception:
        pass


def purger_dechets():
    """Nettoie les fichiers temporaires de dev."""
    for f in ["chatin.json", "output_prompting_proto_query.json", "feed.txt"]:
        p = os.path.join(PIPELINES_DIR, f)
        if os.path.exists(p):
            try:
                os.remove(p)
            except:
                pass


def charger_config_openrouter():
    if not all(os.path.exists(p) for p in [KEY_FILE, MODEL_FILE]):
        print("  ⚠ Config OpenRouter manquante", flush=True)
        return None, None
    with open(KEY_FILE, "r") as f:
        api_key = f.read().strip()
    with open(MODEL_FILE, "r") as f:
        model = f.read().strip()
    return api_key, model


def extraire_texte_reponse(data):
    """Extrait le texte d'une réponse OpenRouter."""
    msg = data.get("choices", [{}])[0].get("message", {})
    content = msg.get("content")
    if not content:
        return None
    content = content.strip()
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and parsed.get("Chat"):
            return str(parsed["Chat"]).strip()
    except json.JSONDecodeError:
        pass
    return content if content else None


def initialiser_plateau():
    """Initialise le plateau via les commandes internes (plus de HTTP)."""
    try:
        with utils.dealer_lock:
            utils.run_cmd("init")
            utils.run_cmd("start")
            dealer.save()
        utils.run_renderer()
        print("  ✓ Plateau initialisé (init + start)", flush=True)
    except Exception as e:
        print(f"  ⚠ init plateau: {e}", flush=True)


def initialiser_llm(api_key, model):
    """Demande au LLM un message d'accueil et l'injecte via masterout."""
    if not api_key or not model:
        print("  ⚠ Config LLM incomplète, skip", flush=True)
        return

    payload = {
        "message_utilisateur": "",
        "carte_revelee": None,
        "resume_symbolique": "Le plateau est préparé. Sept cartes sont face cachées sur la ligne B1-H1.",
        "signal_colonne": None,
        "themes_precedents": [],
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)}],
        "temperature": 0.7,
        "max_tokens": 300,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=20)
        resp.raise_for_status()
        texte = extraire_texte_reponse(resp.json())

        if not texte:
            texte = "L'oracle est prêt. Cliquez sur une carte face cachée pour commencer."
            print("  ⚠ LLM sans contenu, message par défaut", flush=True)

        # Injection directe (plus besoin de HTTP masterout)
        utils.write_chatin(texte)
        utils.executer_commande("no")
        print("  ✓ LLM initialisé", flush=True)

    except Exception as e:
        print(f"  ⚠ LLM erreur: {e}", flush=True)


def demarrer_flask():
    """Lance Flask dans un thread daemon."""
    # Werkzeug silencieux (on gère nos propres logs)
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    app.run(debug=False, host=HOST, port=PORT, threaded=True, use_reloader=False)


def arreter(signum=None, frame=None):
    """Arrêt propre."""
    print(f"\n{'─'*50}\nArrêt de l'oracle...")
    print(f"{'═'*50}\n")
    os._exit(0)


# --------------------------------------------------
# POINT D'ENTRÉE
# --------------------------------------------------
def main():
    liberer_port(PORT)
    purger_dechets()

    print(f"\n{'═'*50}")
    print(f"  ORACLE PRÉSENT — Dame de Trèfle")
    print(f"{'═'*50}\n")

    # 1. Lancer Flask en arrière-plan
    flask_thread = threading.Thread(target=demarrer_flask, daemon=True)
    flask_thread.start()
    print(f"  {GREEN}▶ flask{RESET} démarré sur :{PORT}", flush=True)

    # 2. Attendre que Flask soit prêt
    for _ in range(15):
        try:
            if requests.get(f"http://localhost:{PORT}/state", timeout=2).status_code == 200:
                print("  ✓ Flask prêt", flush=True)
                break
        except:
            pass
        time.sleep(1)
    else:
        print("  ⚠ Flask n'a pas répondu à temps", flush=True)

    # 3. Initialiser le plateau
    initialiser_plateau()

    # 4. Initialiser le LLM
    api_key, model = charger_config_openrouter()
    initialiser_llm(api_key, model)

    print(f"\n  Interface : http://localhost:{PORT}")
    print(f"  Ctrl+C pour arrêter")
    print(f"{'─'*50}\n", flush=True)

    # 5. Boucle principale (keepalive + signaux)
    signal.signal(signal.SIGINT, arreter)
    signal.signal(signal.SIGTERM, arreter)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
