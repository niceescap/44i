# La Rosace — Flutter (Android)

Client mobile de **La Rosace V3**. Même contrat que `rosace_depose.html` :
API `/api/v2` uniquement. Aucune clé LLM dans l’application.

## Première génération native

Depuis ce dossier, avec Flutter installé :

```bash
flutter create --org com.nicee --project-name interpretes44 --platforms android .
flutter pub get
```

Ne pas laisser l’outil écraser `lib/` ni `pubspec.yaml`.

Vérifier `applicationId` = `com.nicee.interpretes44`.

## Lancement

Production (défaut du code) :

```bash
flutter run --dart-define=API_BASE_URL=https://44i.webredirect.org
```

Émulateur vers l’API locale :

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:3252
```

AAB Play Store :

```bash
flutter build appbundle --dart-define=API_BASE_URL=https://44i.webredirect.org
```

## Parité web

Distribution 52 cartes → 3 révélations → interprétation SSE → chat SSE →
export Markdown → don PayPal → liste d’attente Premium → bouton audio
(teaser « fonction premium »).

La V1 (tapis colonnes, `/api/sessions`) n’existe plus dans ce client.
