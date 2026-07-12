#!/usr/bin/env python3
"""
chatbox.py — Endpoint Flask pour la chatbox utilisateur.
"""

import json
import os
from datetime import datetime
from flask import Blueprint, request, jsonify

from llm_handler import interroger_llm
from utils import executer_commande, build_context as load_context

chat_bp = Blueprint('chat', __name__)

CHATIN_FILE = "chatin.json"
FEED_FILE = "feed.txt"


def append_feed(role, text):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(FEED_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {role.upper()}: {text}\n")


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


@chat_bp.route("/chat", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True) or {}
    text = data.get("message", "").strip()
    if not text:
        return jsonify({"status": "error", "message": "empty"}), 400

    append_feed("user", text)

    ctx = load_context()
    signal = ctx.get("memory", {}).get("column_signal")

    chat_text, commande, theme = interroger_llm(
        user_text=text,
        context=ctx,
        signal=signal,
    )
    print(f"[chatbox] commande reçue du LLM : {commande}", flush=True)

    write_json(CHATIN_FILE, {
        "role": "llm",
        "text": chat_text,
        "ts": datetime.now().isoformat(),
    })
    append_feed("llm", chat_text)

    if commande and commande.lower() != "no":
        executer_commande(commande, theme=theme)

    return jsonify({"status": "ok", "commande": commande})


@chat_bp.route("/chat/poll")
def poll_response():
    entry = read_json(CHATIN_FILE, None)
    if entry is None:
        return jsonify({"status": "waiting"})

    try:
        os.remove(CHATIN_FILE)
    except OSError:
        pass

    return jsonify({"status": "ok", "entry": entry})


@chat_bp.route("/chat/history")
def get_history():
    if not os.path.exists(FEED_FILE):
        return jsonify({"lines": []})
    with open(FEED_FILE, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f.readlines()]
    return jsonify({"lines": lines})
