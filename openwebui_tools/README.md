# Outil OpenWebUI — 44 interprètes

Fichier à importer dans OpenWebUI : `44i_symbolique.py`.

## Ressources montées en lecture seule

L’outil attend par défaut :

```txt
/data/44i/extractor/52cartes.json
/data/44i/extractor/qualites.json
/data/44i/chroma_db/
```

Variables optionnelles :

```env
SYMBOLIQUE_EXTRACTOR_DIR=/data/44i/extractor
SYMBOLIQUE_CHROMA_DIR=/data/44i/chroma_db
SYMBOLIQUE_CHROMA_COLLECTION=paires
```

Si ChromaDB est absent, les recherches de cartes, qualités et remarquables restent disponibles ; une paire sans collection disponible renvoie simplement `found: false`.

## Fonctions exposées

- `rechercher_carte(code)`
- `rechercher_paire(carte_a, carte_b)`
- `rechercher_qualite(carte_base, carte_apport)`
- `rechercher_remarquables(cartes)`

Toutes les fonctions retournent une chaîne JSON et sont strictement read-only. Elles ne reçoivent aucun `session_id` et ne peuvent pas modifier le tirage.

## Import OpenWebUI

1. Créer ou ouvrir l’outil Python custom.
2. Remplacer le contenu par `44i_symbolique.py`.
3. Vérifier que le runtime possède `pydantic` et, pour les paires, `chromadb`.
4. Monter les ressources avec des droits de lecture uniquement.
5. Activer l’outil dans le modèle custom.
6. Tester d’abord `rechercher_carte` avec `QC`, puis `rechercher_paire` avec `QC` et `8H`.

Ne pas exposer de clé API dans ce fichier.
