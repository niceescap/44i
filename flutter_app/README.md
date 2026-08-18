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
bash tool/prepare_android.sh   # génère android/ (androidx), copy brand, icône

flutter build apk --release --dart-define=API_BASE_URL=https://44i.webredirect.org
```

APK : `~/44i/flutter_app/build/app/outputs/flutter-apk/app-release.apk`
Tu peux le renommer `La-Rosace-1.5.0.apk` ; Google n’utilise pas ce nom de fichier.

AAB Play Store (plus tard) :

```bash
flutter build appbundle --release --dart-define=API_BASE_URL=https://44i.webredirect.org
```

### Prérequis build
- **Flutter ≥ 3.19** recommandé (le code évite les API >3.22).
- **AndroidX activé** : `android/gradle.properties` est commité dans la branche
  (`android.useAndroidX=true`, RAM limitée pour noe).
- **Assets brand** : `tool/prepare_android.sh` copie `backend/static/brand/bandeau.jpg`
  et `rosace.png` vers `flutter_app/assets/brand/`. Non commités → toujours passer
  par `prepare_android.sh`.

## 📦 Jeu de cartes (à livrer par l’éditeur)

Les visuels des cartes sont **asset-ready** : dès que les fichiers sont présents,
ils remplacent les placeholders. À déposer dans **`flutter_app/assets/cards/`** :

- `back.png` — le dos (une seule face cachée)
- `<code>.png` — une image par carte, 52 fichiers (ex. `6C.png`, `QH.png`, `AD.png`)

Codes : `A`2`3`4`5`6`7`8`9`T`J`Q`K` (hausée) + couleur `C`H`D`S` (Trèfle,
Cœur, Carreau, Pique). Ex. : `KC.png`, `TH.png`, `9D.png`, `AS.png` … (52).

Format conseillé : PNG carré ~512 px, dos et faces au même format
(`BoxFit.fill` les couvre). Tant que les assets sont absents, l’app affiche un
placeholder vectoriel propre (dos `✦` doré, face crème avec le point).

> Le dossier `assets/cards/` ne doit **pas** être vide pour le build (`pubspec` le
> référence) : un `.gitkeep` y est commité. Les PNG s’ajoutent librement.

## UX mode app (1.5.0)

Deux états, basculés par une **animation** (`AnimatedSwitcher`).
1. **Tapis** : rosace + **mini-logs guides** discrets qui orientent le tirage
   (formulation courte « Nom, motif. » tirée au sort, la dernière **pulse**).
2. **À la 3ᵉ carte** : le tapis se replie (rappel du reste), puis **bascule en
   mode ChatBox** : **main de 3 cartes en en-tête**, chat **scrollable** occupant
   tout l’espace, footer compact (Recommencer / Conserver / Don / Premium).

### Chorégraphie du tapis
Reproduite depuis `rosace_depose.html` avec des animations **implicites** (PAS
d’AnimationController) + des timers qui séquencent chaque carte :
- **Deal** : 52 cartes du centre vers les sites, `dealOrder()` (interne→externe),
  *stagger* 1680 ms, *spin* `dealSpin`, vol 2720 ms. Taps après pose complète.
- **Rappel** : les 49 non tirées reviennent au centre, `recallOrder()`
  (externe→interne), *stagger* 1200 ms, *spin* `recallSpin`, vol 2000 ms, fondu.
- **Bascule chat** : `onGathered` (stage) → `beginOracle` → mode ChatBox avec la
  main en tête ; filet de sécurité 12 s dans le contrôleur.

### Versioning
Bump en 3 endroits cohérents : `pubspec.yaml` (`version:`),
`lib/theme.dart` (`appVersionLabel`), `lib/api/rosace_api.dart` (`appVersion`).

## Première génération native (déjà dans le script)

```bash
flutter create --org com.nicee --project-name la_rosace --platforms android .
```

Le script force ensuite `com.nicee.larosace` (sans underscore) et pose l’icône.
Ne pas laisser `flutter create` écraser `lib/` ni `pubspec.yaml`.