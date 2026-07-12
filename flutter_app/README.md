# 44 interprètes — Flutter V1

Front mobile Android connecté uniquement au backend 44i.

## Initialisation native

Depuis ce dossier avec Flutter installé :

```bash
flutter create --org com.nicee --project-name interpretes44 --platforms android .
flutter pub get
```

La génération native ne doit pas remplacer `lib/` ni `pubspec.yaml`.

## Lancement de test

```bash
flutter run --dart-define=API_BASE_URL=https://api.example.com
```

En local :

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:3252
```

Aucune clé OpenWebUI ne doit être ajoutée à Flutter.
