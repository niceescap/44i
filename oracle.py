"""Point d'entrée de test compatible avec l'ancien oracle.py.

L'application V1 est maintenant l'API FastAPI backend.app:app.
"""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "3252")),
        reload=False,
    )
