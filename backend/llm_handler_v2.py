#!/usr/bin/env python3
"""Handler LLM v2 — simple intermédiaire d'affichage.

Aucun system prompt ici : le custom prompt du modèle (OpenWebUI) fait le reste.
Premier message = logs de tirage (cold start). Ensuite, le chat utilisateur.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")
load_dotenv(ROOT / ".env")


def llm_settings() -> dict[str, str]:
    return {
        "url": os.getenv("OPENWEBUI_URL", "").rstrip("/"),
        "key": os.getenv("OPENWEBUI_API_KEY", ""),
        "model": os.getenv("OPENWEBUI_MODEL", "44-interpretes"),
    }


def describe_settings() -> str:
    cfg = llm_settings()
    key = cfg["key"]
    masked = f"{key[:6]}…{key[-4:]}" if len(key) > 12 else ("absente" if not key else "présente")
    return f"url={cfg['url'] or '(vide)'} model={cfg['model']} key={masked}"


def cold_start_message(logs: list[str]) -> str:
    lines = [line.strip() for line in logs if str(line).strip()]
    if not lines:
        return "Tirage de trois cartes. Aucun log symbolique."
    return "\n".join(lines)


async def complete(messages: list[dict[str, str]]) -> str:
    cfg = llm_settings()
    if not cfg["url"] or not cfg["key"]:
        raise RuntimeError(f"LLM non configuré ({describe_settings()})")

    headers = {
        "Authorization": f"Bearer {cfg['key']}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1200,
        "stream": False,
    }
    url = f"{cfg['url']}/api/chat/completions"
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            print(f"[llm_v2] HTTP {response.status_code}: {response.text[:800]}", flush=True)
        response.raise_for_status()
        data = response.json()

    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    text = (content or "").strip()
    if not text:
        raise RuntimeError("réponse LLM vide")
    return text


print(f"[llm_v2] {describe_settings()}", flush=True)
