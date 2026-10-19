import 'dart:async';

import 'package:google_mobile_ads/google_mobile_ads.dart';

/// Interstitiel de transition tirage → oracle.
///
/// Test Ad Unit Android (pas l'App ID) :
/// ca-app-pub-3940256099942544/1033173712
///
/// Ne bloque jamais la consultation : échec, absence ou consentement
/// refusé = [showIfReady] revient tout de suite.
class OracleInterstitial {
  OracleInterstitial._();
  static final OracleInterstitial instance = OracleInterstitial._();

  static const testAdUnitId = 'ca-app-pub-3940256099942544/1033173712';

  InterstitialAd? _ready;
  bool _loading = false;
  bool _sdkReady = false;
  bool _preparing = false;
  bool _wantPreload = false;

  /// UMP puis MobileAds. À appeler au démarrage, sans attendre le résultat.
  Future<void> prepare() async {
    if (_sdkReady || _preparing) return;
    _preparing = true;
    try {
      await _consent();
      final allowed = await ConsentInformation.instance.canRequestAds();
      if (!allowed) return;
      await MobileAds.instance.initialize();
      _sdkReady = true;
      if (_wantPreload) _load();
    } catch (_) {
      // oracle quand même
    } finally {
      _preparing = false;
    }
  }

  Future<void> _consent() async {
    final done = Completer<void>();
    ConsentInformation.instance.requestConsentInfoUpdate(
      ConsentRequestParameters(),
      () {
        ConsentForm.loadAndShowConsentFormIfRequired((_) {
          if (!done.isCompleted) done.complete();
        });
      },
      (_) {
        if (!done.isCompleted) done.complete();
      },
    );
    await done.future.timeout(const Duration(seconds: 12), onTimeout: () {});
  }

  /// Dès la 2e carte, pour que le show après le rappel ne attende pas un load.
  void preload() {
    _wantPreload = true;
    if (!_sdkReady) {
      prepare();
      return;
    }
    _load();
  }

  void _load() {
    if (_ready != null || _loading || !_sdkReady) return;
    _loading = true;
    InterstitialAd.load(
      adUnitId: testAdUnitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (ad) {
          _loading = false;
          _ready = ad;
        },
        onAdFailedToLoad: (_) {
          _loading = false;
          _ready = null;
        },
      ),
    );
  }

  /// Show si une ad est déjà chargée. Sinon retour immédiat.
  /// L'objet est consommé : dispose après dismiss ou échec de show.
  Future<void> showIfReady() async {
    final ad = _ready;
    if (ad == null) return;
    _ready = null;
    _wantPreload = false;
    final done = Completer<void>();
    ad.fullScreenContentCallback = FullScreenContentCallback(
      onAdDismissedFullScreenContent: (shown) {
        shown.dispose();
        if (!done.isCompleted) done.complete();
      },
      onAdFailedToShowFullScreenContent: (shown, _) {
        shown.dispose();
        if (!done.isCompleted) done.complete();
      },
    );
    try {
      await ad.show();
      await done.future;
    } catch (_) {
      ad.dispose();
    }
  }
}
