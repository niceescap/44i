# AdMob — point d’insertion (recherche, pas d’implémentation)

Question : où coller AdMob pour qu’il apparaisse **après la fin de l’animation du tirage** et **avant la réponse du modèle** ?

Réponse courte : dans `RosaceController.beginOracle()`, **avant** `await _interpret()`. Format Google pour cet emplacement : **interstitiel** (plein écran, rupture naturelle).

## Flux actuel (1.5.3+9, `feature/play-release-v2`)

```
3e carte révélée
  → phase = 'recalling'          RosaceController.reveal()
  → animation rappel 49 cartes   RosaceStage._startRecall()
  → onGathered après 3200 ms     HandMotion.gatherMs
  → beginOracle()
       phase = 'oracle'          HomeScreen bascule ChatPanel
       _interpret()              stream SSE → bulle oracle
```

La symbolique (mini-logs) est déjà écrite pendant les clics, dans `reveal()`, via `_addGuide(RevelationGuides.cardGuideLine(...))`. Rien à bouger de ce côté.

## Où, exactement

| Quoi | Où |
|---|---|
| Fichier | `flutter_app/lib/state/rosace_controller.dart` |
| Fonction | `beginOracle()` (l.157) puis `_interpret()` (l.166) |
| Fin d’animation | `flutter_app/lib/widgets/rosace_stage.dart` → `_startRecall()`, timer `HandMotion.gatherMs` (3200 ms) → `onGathered` |
| Câblage UI | `flutter_app/lib/screens/home_screen.dart` : `onGathered: controller.beginOracle` |
| Réponse modèle | `_interpret()` : ajoute une `ChatMessage` oracle vide, lit `api.interpretStream`, `ChatPanel` affiche la bulle (marque d’attente si `content.isEmpty`) |
| Filet | `reveal()` : `Future.delayed(12s)` rappelle `beginOracle()` si `phase` est encore `'recalling'` |

Aujourd’hui `beginOracle()` enchaîne tout de suite :

```dart
phase = 'oracle';
notifyListeners();
await _interpret();   // ← insérer l’interstitiel AVANT cette ligne
```

Ne pas toucher à `onGathered` dans le stage : l’animation doit se terminer, puis l’annonce, puis le stream.

## Format Google pour cet emplacement

[Interstitial ads](https://developers.google.com/admob/flutter/interstitial) : plein écran, « natural transition points » (entre deux activités, après un niveau). C’est le format standard pour une pause de quelques secondes entre une action terminée (tirage + animation) et un nouveau contenu (oracle). Pas de bannière (persistante), pas d’app-open (lancement), pas de rewarded (opt-in).

Plugin : [`google_mobile_ads`](https://pub.dev/packages/google_mobile_ads)  
Guide : [Get started (Flutter)](https://developers.google.com/admob/flutter/quick-start)

L’interstitiel se ferme par l’utilisateur (croix / skip). Il n’y a pas de « timer 3 s puis auto-close » dans le SDK : `onAdDismissedFullScreenContent` (ou échec de show/load) déclenche alors `_interpret()`.

## Modifications nécessaires (future version, pas maintenant)

1. **Précharger** l’interstitiel (idéalement dès la 2ᵉ carte, ou au `deal`) pour ne pas bloquer sur un spinner à `beginOracle()`.
2. Dans `beginOracle()` : `show()` l’annonce déjà chargée ; **seulement après dismiss / fail** → `phase = 'oracle'` + `_interpret()`. Ne pas lancer le SSE pendant l’annonce (jetons + bulle cachée).
3. `pubspec.yaml` : dépendance `google_mobile_ads`.
4. `main.dart` : `MobileAds.instance.initialize()` après le consentement.
5. `AndroidManifest.xml` : `com.google.android.gms.ads.APPLICATION_ID` (App ID AdMob, pas l’ad unit). `INTERNET` est déjà là. Fusion possible de `com.google.android.gms.permission.AD_ID`.
6. **UMP / RGPD** (France = EEE) : [Privacy & messaging](https://developers.google.com/admob/flutter/privacy) avant tout init ads.
7. Compte AdMob : App ID + ad unit **Interstitial**. En debug : IDs de test Google (`ca-app-pub-3940256099942544/1033173712`).
8. Privacy policy + Data safety Play (publicité, identifiant pub) — hors code.

Hors scope de cette note : compte AdMob, eCPM, AAB. Ne pas merger dans `main`. Ne pas builder.
