#!/usr/bin/env python3
"""Handler LLM v2 — OpenRouter direct.

Clé : API_KEY_44iV2
Modèle : @preset/dame-de-trefle
Aucun system prompt ici : le preset porte les instructions.
Premier message = logs de tirage (cold start).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")
load_dotenv(ROOT / ".env")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "@preset/dame-de-trefle"


def llm_settings() -> dict[str, str]:
    return {
        "url": os.getenv("OPENROUTER_URL", OPENROUTER_URL).rstrip("/"),
        "key": os.getenv("API_KEY_44iV2", ""),
        "model": os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
    }


def describe_settings() -> str:
    cfg = llm_settings()
    key = cfg["key"]
    masked = f"{key[:6]}…{key[-4:]}" if len(key) > 12 else ("absente" if not key else "présente")
    return f"url={cfg['url']} model={cfg['model']} key={masked}"


def cold_start_message(logs: list[str]) -> str:
    lines = [line.strip() for line in logs if str(line).strip()]
    if not lines:
        return "Tirage de trois cartes. Aucun log symbolique."
    return "\n".join(lines)


def _extract_text(content: Any) -> str:
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    if not isinstance(content, str):
        return ""
    text = content.strip()
    if not text:
        return ""
    if text.startswith("```"):
        text = text.strip("`").replace("json\n", "", 1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        parsed = None
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                parsed = None
    if isinstance(parsed, dict) and parsed.get("Chat"):
        return str(parsed["Chat"]).strip()
    return text


async def complete(messages: list[dict[str, str]]) -> str:
    cfg = llm_settings()
    if not cfg["key"]:
        raise RuntimeError(f"LLM non configuré ({describe_settings()})")

    headers = {
        "Authorization": f"Bearer {cfg['key']}",
        "Content-Type": "application/json; charset=utf-8",
        "HTTP-Referer": "https://44i.webredirect.org",
        "X-Title": "La Rosace",
    }
    body: dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1200,
    }
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(cfg["url"], headers=headers, content=payload)
        if response.status_code >= 400:
            print(f"[llm_v2] HTTP {response.status_code}: {response.text[:800]}", flush=True)
        response.raise_for_status()
        data = response.json()

    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = _extract_text(message.get("content"))
    if not text:
        raise RuntimeError("réponse LLM vide")
    return text


def _delta_text(payload: dict[str, Any]) -> str:
    choice = (payload.get("choices") or [{}])[0]
    delta = choice.get("delta") or {}
    piece = delta.get("content")
    if piece is None:
        message = choice.get("message") or {}
        piece = message.get("content")
    if isinstance(piece, list):
        piece = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in piece
        )
    return piece if isinstance(piece, str) else ""


async def complete_stream(messages: list[dict[str, str]]):
    cfg = llm_settings()
    if not cfg["key"]:
        raise RuntimeError(f"LLM non configuré ({describe_settings()})")

    headers = {
        "Authorization": f"Bearer {cfg['key']}",
        "Content-Type": "application/json; charset=utf-8",
        "HTTP-Referer": "https://44i.webredirect.org",
        "X-Title": "La Rosace",
    }
    body: dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1200,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", cfg["url"], headers=headers, json=body) as response:
            if response.status_code >= 400:
                err = (await response.aread()).decode("utf-8", "replace")[:800]
                print(f"[llm_v2] HTTP {response.status_code}: {err}", flush=True)
                response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                piece = _delta_text(parsed)
                if piece:
                    yield piece


print(f"[llm_v2] {describe_settings()}", flush=True)
