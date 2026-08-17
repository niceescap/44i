# La Rosace — Flutter (Android)

Application **La Rosace**. Éditeur : **44 interprètes**. Repo : `44i`.

| Visible (Store, icône, titre) | Technique (invisible) |
|---|---|
| La Rosace | `applicationId` = `com.nicee.larosace` |
| Éditeur : 44 interprètes | module Dart = `la_rosace` |
| Icône = `logocarre.jpg` | dossier = `flutter_app/` |

API uniquement `https://44i.webredirect.org` `/api/v2`. Aucune clé LLM dans l’app.

`com.nicee.interpretes44` est **réservé** à une éventuelle app-catalogue de l’éditeur.

## Build sur noe (Termux)

Ne pas merger cette branche dans `main`. Ne pas relancer `44i.service` pendant le build.

```bash
cd ~/44i
git fetch origin
git checkout feature/la-rosace-identity
git pull origin feature/la-rosace-identity

cd flutter_app
chmod +x tool/prepare_android.sh
bash tool/prepare_android.sh

flutter build apk --release --dart-define=API_BASE_URL=https://44i.webredirect.org
```

APK : `~/44i/flutter_app/build/app/outputs/flutter-apk/app-release.apk`

Tu peux le renommer `La-Rosace.apk` pour le transfert ; Google n’utilise pas ce nom de fichier.

AAB Play Store (plus tard) :

```bash
flutter build appbundle --release --dart-define=API_BASE_URL=https://44i.webredirect.org
```

## Première génération native (déjà dans le script)

```bash
flutter create --org com.nicee --project-name la_rosace --platforms android .
```

Le script force ensuite `com.nicee.larosace` (sans underscore) et pose l’icône.

Ne pas laisser `flutter create` écraser `lib/` ni `pubspec.yaml`.
