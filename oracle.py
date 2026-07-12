"""Lanceur de test pour l'API 44 interprètes sur le port 3252."""

import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / "backend" / ".env")

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "3252")),
        reload=False,
    )
