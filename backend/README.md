# 44 interprètes — API V1

Backend FastAPI minimal pour l’application mobile.

## Principes

- sessions anonymes en mémoire uniquement ;
- expiration glissante de 45 minutes ;
- aucune base de données ni écriture de consultation ;
- export Markdown généré à la demande ;
- Flutter appelle uniquement cette API ;
- OpenWebUI est optionnel et reste derrière l’API.

## Lancement local

Depuis la racine du dépôt :

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Créer `backend/.env` à partir de `.env.example` pour activer le relais OpenWebUI. Sans configuration OpenWebUI, l’API fournit une réponse symbolique de secours.

## Docker

```bash
cp backend/.env.example backend/.env
# renseigner les variables OpenWebUI si nécessaire
docker compose up --build
```

Documentation interactive : `http://localhost:8000/docs`.

## Contrat de base

1. `POST /api/sessions`
2. `POST /api/sessions/{id}/cards/reveal` avec `{ "slot": "B1" }`
3. `POST /api/sessions/{id}/messages` avec `{ "message": "..." }`
4. `GET /api/sessions/{id}/export`
5. `POST /api/sessions/{id}/reset`

Cette première tranche ne contient pas encore l’application Flutter ni le rate limiting de production.
