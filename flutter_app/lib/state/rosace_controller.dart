import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/rosace_api.dart';
import '../cards/deck.dart';
import '../l10n/app_strings.dart';
import '../models/rosace_models.dart';

class RosaceController extends ChangeNotifier {
  RosaceController({RosaceApi? api, String? locale})
      : locale = locale ?? deviceLocale(),
        strings = AppStrings(locale ?? deviceLocale()),
        api = api ?? RosaceApi(locale: locale ?? deviceLocale());

  final RosaceApi api;
  final String locale;
  final AppStrings strings;
  final _rng = Random();

  String? sessionId;
  String phase = 'table';
  bool busy = false;
  bool dealing = false;
  String? error;
  String visitorId = '';
  String visitId = '';
  List<CardPlacement> placements = [];
  final List<int> chosen = [];
  final List<ChatMessage> messages = [];
  bool chatReady = false;
  bool premiumThanks = false;

  String pick(List<String> lines) => lines[_rng.nextInt(lines.length)];

  Future<void> start() async {
    final prefs = await SharedPreferences.getInstance();
    visitorId = prefs.getString('la-rosace-visitor') ?? '';
    if (visitorId.length < 8) {
      visitorId = 'v-${DateTime.now().microsecondsSinceEpoch}-${_rng.nextInt(1 << 32)}';
      await prefs.setString('la-rosace-visitor', visitorId);
    }
    visitId = 't-${DateTime.now().microsecondsSinceEpoch}-${_rng.nextInt(1 << 20)}';
    await deal();
  }

  Future<void> deal({double width = 360, double height = 360}) async {
    busy = true;
    dealing = true;
    error = null;
    chatReady = false;
    phase = 'table';
    chosen.clear();
    messages
      ..clear()
      ..add(ChatMessage(role: 'oracle', content: pick(strings.askLines), guide: true));
    notifyListeners();
    try {
      final state = await api.createSession(width: width, height: height, locale: locale);
      sessionId = state.sessionId;
      placements = state.sites.map((site) => CardPlacement(site: site)).toList();
      await api.trackVisit(visitId: visitId, visitorId: visitorId, sessionId: sessionId);
      await api.trackEvent(visitId: visitId, visitorId: visitorId, type: 'deal', sessionId: sessionId);
    } catch (exception) {
      error = strings.tableFail;
      debugPrint('$exception');
      await track('error', code: 'table');
    } finally {
      busy = false;
      dealing = false;
      notifyListeners();
    }
  }

  Future<void> reveal(int index) async {
    if (sessionId == null || dealing || phase != 'table') return;
    if (index < 0 || index >= placements.length) return;
    final placement = placements[index];
    if (placement.revealed) return;
    dealing = true;
    notifyListeners();
    try {
      final data = await api.reveal(sessionId!, placement.site.id);
      final chosenRows = ((data['chosen'] as List?) ?? []).cast<dynamic>();
      final hit = chosenRows.cast<Map>().firstWhere(
            (row) => row['site_id'] == placement.site.id,
            orElse: () => {},
          );
      final code = hit['card'] as String?;
      if (code == null) throw Exception('réponse sans carte');
      placement
        ..card = PlayingCard.fromCode(code)
        ..revealed = true;
      chosen.add(index);
      if (chosen.length == 1) {
        messages.add(ChatMessage(role: 'oracle', content: pick(strings.moreLines), guide: true));
      } else if (chosen.length == 2) {
        messages.add(ChatMessage(role: 'oracle', content: pick(strings.lastLines), guide: true));
      } else if (chosen.length >= 3) {
        phase = 'oracle';
        messages.add(ChatMessage(
          role: 'oracle',
          content: '${pick(strings.waitLines)} ${pick(strings.discLines)}',
          guide: true,
        ));
        notifyListeners();
        await _interpret();
      }
    } catch (exception) {
      error = exception.toString();
    } finally {
      dealing = false;
      notifyListeners();
    }
  }

  Future<void> _interpret() async {
    if (sessionId == null) return;
    final bubble = ChatMessage(role: 'oracle', content: '');
    messages.add(bubble);
    notifyListeners();
    try {
      final acc = StringBuffer();
      await for (final piece in api.interpretStream(sessionId!)) {
        acc.write(piece);
        messages[messages.length - 1] = ChatMessage(role: 'oracle', content: acc.toString());
        notifyListeners();
      }
      if (acc.isEmpty) {
        messages[messages.length - 1] = ChatMessage(role: 'oracle', content: strings.silent);
      }
    } catch (exception) {
      debugPrint('$exception');
      messages[messages.length - 1] = ChatMessage(role: 'oracle', content: strings.silent);
    }
    chatReady = true;
    notifyListeners();
  }

  Future<void> send(String text) async {
    final value = text.trim();
    if (sessionId == null || !chatReady || value.isEmpty || dealing) return;
    dealing = true;
    messages.add(ChatMessage(role: 'user', content: value));
    messages.add(const ChatMessage(role: 'oracle', content: ''));
    notifyListeners();
    try {
      final acc = StringBuffer();
      await for (final piece in api.messageStream(sessionId!, value)) {
        acc.write(piece);
        messages[messages.length - 1] = ChatMessage(role: 'oracle', content: acc.toString());
        notifyListeners();
      }
      if (acc.isEmpty) {
        messages[messages.length - 1] = ChatMessage(role: 'oracle', content: strings.silent);
      }
    } catch (exception) {
      messages[messages.length - 1] = ChatMessage(role: 'oracle', content: strings.silent);
    } finally {
      dealing = false;
      notifyListeners();
    }
  }

  Future<void> track(String type, {String? email}) {
    return api.trackEvent(
      visitId: visitId,
      visitorId: visitorId,
      type: type,
      sessionId: sessionId,
      email: email,
    );
  }

  String exportMarkdown() {
    final now = DateTime.now();
    String pad(int n) => n.toString().padLeft(2, '0');
    final stamp =
        '${pad(now.day)}/${pad(now.month)}/${now.year} ${pad(now.hour)}:${pad(now.minute)}';
    final lines = <String>[
      '# La Rosace',
      '',
      strings.tagline,
      strings.subtitle,
      '',
      'Code de session : ${sessionId ?? 'inconnu'}',
      'Date : $stamp',
      '',
      '## Avertissement',
      '',
      'La Rosace est une application de divertissement. Les interprétations sont issues d\'ouvrages ésotériques et générées par intelligence artificielle.',
      '',
      '## Chat',
      '',
    ];
    final chat = messages.where((item) => !item.guide).toList();
    if (chat.isEmpty) {
      lines.add(strings.none);
    } else {
      for (final item in chat) {
        final who = item.role == 'user' ? strings.user : strings.oracle;
        lines.add('$who: ${item.content}');
        lines.add('');
      }
    }
    return lines.join('\n');
  }
}
