# La Rosace — Flutter (Android)

Application **La Rosace**. Éditeur : **44 interprètes**. Repo : `44i`.

| Visible (Store, icône, titre) | Technique (invisible) |
|---|---|
| La Rosace | `applicationId` = `com.nicee.larosace` |
| Éditeur : 44 interprètes | module Dart = `la_rosace` |
| Icône = `logocarre.jpg` | dossier = `flutter_app/` |
| Version affichée | `1.5.0+6` |

API uniquement `https://44i.webredirect.org` `/api/v2`. Aucune clé LLM dans l’app.

`com.nicee.interpretes44` est **réservé** à une éventuelle app-catalogue de l’éditeur.

## Build sur noe (Termux)

Ne pas merger cette branche dans `main`. Ne pas relancer `44i.service` pendant le build.

```bash
cd ~/44i
git fetch origin
git checkout feature/flutter-choreography-v1.5
git pull origin feature/flutter-choreography-v1.5

cd flutter_app
chmod +x tool/prepare_android.sh
bash tool/prepare_android.sh   # génère android/ (androidx), copie brand, icône

flutter build apk --release --dart-define=API_BASE_URL=https://44i.webredirect.org
```

APK : `~/44i/flutter_app/build/app/outputs/flutter-apk/app-release.apk`
Tu peux le renommer `La-Rosace-1.5.0.apk` ; Google n’utilise pas ce nom de fichier.

AAB Play Store (plus tard) :

```bash
flutter build appbundle --release --dart-define=API_BASE_URL=https://44i.webredirect.org
```

### Prérequis build
- **Flutter ≥ 3.19** recommandé (le code évite les API >3.22, p. ex. plus de
  `ColorScheme.fromSeed(surface:)`).
- **AndroidX activé** : `android/gradle.properties` est commité dans la branche
  (`android.useAndroidX=true`, RAM limitée pour noe).
- **Assets brand** : `tool/prepare_android.sh` copie `backend/static/brand/bandeau.jpg`
  et `rosace.png` vers `flutter_app/assets/brand/`. Ces fichiers ne sont pas commités
  (`.gitkeep` seul) → toujours passer par `prepare_android.sh`.

### Versionning
Bump de version en 3 endroits cohérents :
`pubspec.yaml` (`version:`), `lib/theme.dart` (`appVersionLabel`),
`lib/api/rosace_api.dart` (`appVersion` du User-Agent).

## Chorégraphie du tapis (1.5.0)

Reproduite depuis `rosace_depose.html` avec des animations **implicites** (PAS
d’AnimationController, historiquement inopérant sur l’APK) + des timers qui
séquencent chaque carte :
- **Deal** : 52 cartes du centre vers les sites, ordre interne→externe
  (`HandMotion.dealOrder`), *stagger* 1680 ms, *spin* `dealSpin`, vol 2720 ms.
  Les taps ne sont autorisés qu’après la pose complète (`onDealt` à 4400 ms).
- **Rappel** : les 49 non tirées reviennent au centre, ordre externe→interne
  (`recallOrder`), *stagger* 1200 ms, *spin* `recallSpin`, vol 2000 ms, fondu.
- **Main** : les 3 choisies s’éventaillent en `HAND_SLOTS` (scale 1.52) pendant
  ~1,6 s, puis **dévoilement** vers `ORACLE_SLOTS` (scale 2.15) à la phase oracle.
- `onGathered` (stage) déclenche `beginOracle` ; un filet de sécurité de 12 s
  dans le contrôleur garantit le démarrage même si l’écran est détaché.

## Première génération native (déjà dans le script)

```bash
flutter create --org com.nicee --project-name la_rosace --platforms android .
```

Le script force ensuite `com.nicee.larosace` (sans underscore) et pose l’icône.
Ne pas laisser `flutter create` écraser `lib/` ni `pubspec.yaml`.
