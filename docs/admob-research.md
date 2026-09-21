# AdMob — mémoire technique de décision

Cahier pour un futur agent codeur. **Aucune implémentation dans cette version.**
Branche de référence : `feature/play-release-v2` (app en test fermé 1.5.3+9).

Décision en une phrase :

> Afficher un `InterstitialAd` de test après l’animation de regroupement des trois cartes et avant `_interpret()`. Précharger si possible. Attendre la fermeture ou gérer l’échec, puis seulement lancer le streaming IA. Si l’ad n’est pas disponible, continuer directement vers l’oracle.

---

## 1. Format retenu

- SDK : **Google Mobile Ads Flutter** (`google_mobile_ads`).
- Format : **`InterstitialAd` uniquement**.
- Interdit : bannière, rewarded, native, app-open.
- Rôle : transition plein écran entre deux phases de la consultation (tirage terminé → oracle).
- L’utilisateur ferme l’annonce (croix / skip). Pas de timer d’auto-close dans le SDK.

Docs : [Interstitial (Flutter)](https://developers.google.com/admob/flutter/interstitial) · [Get started](https://developers.google.com/admob/flutter/quick-start)

---

## 2. Position exacte dans le flux

Flux **à conserver** :

```
3e carte révélée
  → symbolique locale existante          reveal() / _addGuide(cardGuideLine)
  → animation de regroupement            RosaceStage._startRecall()
  → InterstitialAd                       NOUVEAU — ici seulement
  → fermeture ou échec / absence d’ad
  → interprétation IA                    _interpret()
  → streaming SSE actuel                 api.interpretStream
```

### Ancres code (ne pas déplacer la révélation ni la symbolique)

| Rôle | Fichier | Élément |
|---|---|---|
| Hook d’insertion | `flutter_app/lib/state/rosace_controller.dart` | `beginOracle()` |
| Stream IA | même fichier | `_interpret()` |
| Fin d’animation | `flutter_app/lib/widgets/rosace_stage.dart` | `_startRecall()` → timer `HandMotion.gatherMs` (3200 ms) → `onGathered` |
| Câblage | `flutter_app/lib/screens/home_screen.dart` | `onGathered: controller.beginOracle` |
| Affichage bulle | `flutter_app/lib/widgets/chat_panel.dart` | bulle oracle ; `content.isEmpty` → marque d’attente |
| Symbolique (inchangée) | `rosace_controller.dart` `reveal()` | `_addGuide(RevelationGuides.cardGuideLine(...))` pendant les 3 clics |

Séquence actuelle de `beginOracle()` :

```dart
if (sessionId == null || phase != 'recalling') return;
phase = 'oracle';          // HomeScreen bascule ChatPanel (_chatMode)
dealing = false;
_addGuide(...wait + disclaimer...);
notifyListeners();
await _interpret();        // ← l’interstitiel s’intercale AVANT cet appel
```

Ne pas modifier `onGathered` dans le stage : l’animation doit **finir**, puis l’ad, puis le SSE.

---

## 3. Règle de consommation IA

**Le streaming SSE ne démarre pas pendant l’interstitiel.**

Ordre futur obligatoire :

```
show ad
  → onAdDismissedFullScreenContent
    ou onAdFailedToShowFullScreenContent
    ou pas d’ad chargée / load failed
  → _interpret()
```

- Pas d’ad, load KO, show KO → **continuer vers l’oracle**. La pub ne bloque jamais la consultation.
- Ne pas ouvrir le SSE « en dessous » de l’annonce (jetons brûlés, bulle invisible).

---

## 4. Préchargement

Orientation d’implémentation (pas maintenant) :

- `InterstitialAd.load` **avant** le moment du show.
- Moment préféré : dès la **2ᵉ carte** révélée, sinon au `deal()` une fois la session créée.
- But : à `beginOracle()`, `show()` une ad déjà en mémoire. Pas de spinner artificiel après l’animation.
- Si le preload n’est pas prêt à `beginOracle()` : ne pas attendre indéfiniment → oracle.

---

## 5. Identifiants — bien distinguer les trois

| Identifiant | Rôle | Où |
|---|---|---|
| **AdMob App ID** | identifie l’app auprès d’AdMob | `AndroidManifest` : `com.google.android.gms.ads.APPLICATION_ID` |
| **Ad Unit ID** | unité *Interstitial* de prod | passé à `InterstitialAd.load` |
| **Test Ad Unit ID** | tests dev + test fermé | `InterstitialAd.load` tant que l’on n’est pas en prod ads |

**Test Android officiel Google (ad unit interstitial, PAS l’App ID) :**

```
ca-app-pub-3940256099942544/1033173712
```

L’App ID de test Google (manifest uniquement, distinct) est `ca-app-pub-3940256099942544~3347511713` — ne pas le coller dans `InterstitialAd.load`.

Prod : remplacer App ID **et** Ad Unit ID par les vrais, jamais committer un ID prod dans un chemin de test.

---

## 6. Cycle de vie SDK

Utilisation prévue :

1. `InterstitialAd.load(...)` → callback `onAdLoaded` / `onAdFailedToLoad`.
2. Sur l’instance : `fullScreenContentCallback = FullScreenContentCallback(...)`.
3. `InterstitialAd.show()`.
4. `onAdDismissedFullScreenContent` → `ad.dispose()` → `_interpret()`.
5. `onAdFailedToShowFullScreenContent` → `ad.dispose()` → `_interpret()`.
6. `onAdFailedToLoad` (preload) : garder `_ad == null` ; à `beginOracle()` → `_interpret()` direct.

**Un interstitiel chargé n’est pas réutilisable.** Après show (succès ou échec d’affichage), l’objet est consommé : `dispose()`, puis un nouveau `load` si un prochain tirage en a besoin.

Ne pas empiler plusieurs instances. Une ad préchargée max.

---

## 7. Consentement (orientation technique)

- Utiliser **UMP** (User Messaging Platform, plugin `google_mobile_ads`) **avant** toute requête pub, dès que requis.
- Utilisateurs **EEE / UK / Suisse** : ne pas `load` / `initialize` ads tant que l’état de consentement ne le permet pas.
- Si le consentement n’autorise pas les ads : **pas d’ad, oracle quand même** (même règle que l’échec de load).
- Doc : [Privacy & messaging (Flutter)](https://developers.google.com/admob/flutter/privacy)

Hors de ce document : calendrier Play, Data safety, copy privacy, stratégie commerciale.

---

## 8. Point d’attention — double `beginOracle()`

Aujourd’hui deux chemins :

1. `onGathered` (fin réelle de l’animation, ~3200 ms).
2. Filet dans `reveal()` : `Future.delayed(12s)` si `phase == 'recalling'` → `beginOracle()`.

`beginOracle()` a déjà un garde `if (phase != 'recalling') return;` puis pose `phase = 'oracle'`.

La future implémentation **doit** :

- rester idempotente : un seul show, un seul `_interpret()` par tirage ;
- si l’ad est à l’écran quand le filet 12 s se déclenche : le garde de phase (ou un flag `oracleStarted` / `adShowing`) doit empêcher un second show et un second SSE ;
- ne pas laisser le filet lancer `_interpret()` pendant que l’interstitiel est visible.

---

## Hors scope jusqu’à l’implémentation

Pas de `pubspec.yaml`, pas de manifest, pas de `main.dart`, pas de version, pas d’AAB, pas de merge `main`.
