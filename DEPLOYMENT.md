# Déploiement permanent — 44 interprètes

## Service API

Le conteneur `api` est conçu pour un service permanent : `restart: unless-stopped` est déjà défini dans `docker-compose.yml` et l'API expose `GET /health` pour la supervision.

```bash
cp backend/.env.example backend/.env
# renseigner uniquement les secrets sur le serveur
sudo docker compose up -d --build
curl -fsS http://127.0.0.1:3252/health
```

Placez l'API derrière un proxy TLS (Nginx, Caddy ou équivalent) et exposez uniquement HTTPS au client Android. `OPENWEBUI_API_KEY` reste exclusivement dans `backend/.env`, jamais dans Flutter.

> **Important : un seul worker Uvicorn.** Les sessions anonymes temporaires sont actuellement conservées en mémoire. Plusieurs workers ou réplicas ne partageraient pas les tirages. Une migration vers Redis est nécessaire avant tout déploiement horizontal.

## Langue

L'application Flutter lit la locale de l'OS au démarrage et envoie son tag BCP-47 (`fr-FR`, `en-GB`, etc.) à `POST /api/sessions`. L'API le normalise vers `fr` ou `en`, avec le français comme repli, puis conserve cette langue pendant toute la session. La langue est retournée dans `state.language` et transmise au modèle OpenWebUI.

Les clients plus anciens restent compatibles : une création de session sans corps ou sans `locale` utilise le français.

## Publication Play Store

Avant publication :

- générer le projet Android avec le package `com.nicee.interpretes44` ;
- configurer une URL HTTPS de production via `--dart-define=API_BASE_URL=https://…` ;
- ajouter une politique de confidentialité publique et sa déclaration Data safety ;
- documenter que les consultations sont anonymes et temporaires, sans compte ni historique persistant ;
- indiquer que le traitement des messages est temporairement effectué par le backend et son service OpenWebUI ;
- fournir icône 512×512, feature graphic 1024×500, captures, classification de contenu et métadonnées localisées ;
- vérifier qu'aucune clé, URL interne ou identifiant de fournisseur n'est empaqueté dans l'application.
