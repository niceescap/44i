import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';

const languageLabels = <String, String>{
  'fr': 'Français', 'en': 'English', 'es': 'Español', 'it': 'Italiano',
  'de': 'Deutsch', 'nl': 'Nederlands', 'pt': 'Português', 'pl': 'Polski',
  'hu': 'Magyar', 'sr': 'Српски', 'ru': 'Русский', 'ar': 'العربية',
  'he': 'עברית', 'zh': '中文', 'th': 'ไทย', 'ja': '日本語', 'ko': '한국어',
  'hi': 'हिन्दी', 'id': 'Bahasa Indonesia', 'tr': 'Türkçe', 'vi': 'Tiếng Việt',
};

String initialLanguage() {
  final language = ui.PlatformDispatcher.instance.locale.languageCode.toLowerCase();
  return languageLabels.containsKey(language) ? language : 'fr';
}

// Updated by the selector; used for the small amount of UI copy that is
// currently bundled in French and English. Oracle answers use all languages.
final activeLanguage = ValueNotifier<String>(initialLanguage());
String tr(String french, String english) => activeLanguage.value == 'en' ? english : french;

String get disclaimer => tr(
  '44 interprètes est une application symbolique et divertissante. Les interprétations ne remplacent pas un avis médical, juridique, financier ou professionnel.',
  '44 interpreters is a symbolic entertainment application. Interpretations do not replace medical, legal, financial, or professional advice.',
);

class ApiClient {
  ApiClient() : baseUrl = const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:3252');
  final String baseUrl;

  Future<Map<String, dynamic>> createSession(String locale) async => _getPost('/api/sessions', {'locale': locale});
  Future<Map<String, dynamic>> reveal(String id, String slot) async => _getPost('/api/sessions/$id/cards/reveal', {'slot': slot});
  Future<Map<String, dynamic>> state(String id) async => _get('/api/sessions/$id/state');
  Future<Map<String, dynamic>> message(String id, String value) async => _getPost('/api/sessions/$id/messages', {'message': value});
  Future<String> export(String id) async {
    final response = await http.get(Uri.parse('$baseUrl/api/sessions/$id/export'));
    if (response.statusCode >= 400) throw Exception('Export impossible (${response.statusCode})');
    return response.body;
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await http.get(Uri.parse('$baseUrl$path'));
    return _decode(response);
  }

  Future<Map<String, dynamic>> _getPost(String path, Map<String, dynamic> body) async {
    final response = await http.post(Uri.parse('$baseUrl$path'), headers: {'Content-Type': 'application/json'}, body: jsonEncode(body));
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    final value = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      throw Exception(value is Map ? (value['detail'] ?? 'Erreur serveur') : 'Erreur serveur');
    }
    return Map<String, dynamic>.from(value as Map);
  }
}

class OracleMessage {
  const OracleMessage(this.role, this.content);
  final String role;
  final String content;
}

void main() => runApp(const InterpretesApp());

class InterpretesApp extends StatelessWidget {
  const InterpretesApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        title: '44 interprètes',
        supportedLocales: const [Locale('fr'), Locale('en')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        localeResolutionCallback: (deviceLocale, supportedLocales) {
          final language = deviceLocale?.languageCode.toLowerCase();
          return supportedLocales.firstWhere(
            (locale) => locale.languageCode == language,
            orElse: () => const Locale('fr'),
          );
        },
        theme: ThemeData(
          brightness: Brightness.dark,
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff9c6acb), brightness: Brightness.dark),
          scaffoldBackgroundColor: const Color(0xff0d0717),
          useMaterial3: true,
        ),
        home: const HomeScreen(),
      );
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final api = ApiClient();
  final messages = <OracleMessage>[];
  Map<String, dynamic>? session;
  String? sessionId;
  int tab = 0;
  bool busy = false;
  String? error;
  String language = initialLanguage();

  List<Map<String, dynamic>> get cards => ((session?['cards'] as List?) ?? []).map((item) => Map<String, dynamic>.from(item as Map)).toList();
  List<Map<String, dynamic>> get faceDown => cards.where((card) => card['face'] == 'down').toList();
  List<Map<String, dynamic>> get faceUp => cards.where((card) => card['face'] == 'up').toList();

  @override
  void initState() {
    super.initState();
    _newSession();
  }

  Future<void> _newSession() async {
    setState(() { busy = true; error = null; });
    try {
      // The backend normalizes this value and keeps it for the whole anonymous session.
      final result = await api.createSession(language);
      setState(() { sessionId = result['session_id'] as String; session = Map<String, dynamic>.from(result['state'] as Map); messages.clear(); });
    } catch (exception) {
      setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _selectLanguage(String? value) async {
    if (value == null || value == language || busy) return;
    setState(() {
      language = value;
      activeLanguage = value;
    });
    // A session has one language. Start a fresh anonymous consultation rather
    // than mixing oracle messages or exports in different languages.
    await _newSession();
  }

  Future<void> _reveal(String slot) async {
    if (sessionId == null || busy) return;
    setState(() { busy = true; error = null; });
    try {
      final result = await api.reveal(sessionId!, slot);
      setState(() {
        session = result;
        final stateMessages = ((result['messages'] as List?) ?? []);
        messages..clear()..addAll(stateMessages.map((item) => OracleMessage(item['role'] as String, item['content'] as String)));
        tab = 0;
      });
    } catch (exception) {
      setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _sendMessage(String value) async {
    if (sessionId == null || value.trim().isEmpty || busy) return;
    setState(() { busy = true; messages.add(OracleMessage('user', value.trim())); error = null; });
    try {
      final result = await api.message(sessionId!, value.trim());
      setState(() => messages.add(OracleMessage('oracle', result['content'] as String)));
    } catch (exception) {
      setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _shareExport() async {
    if (sessionId == null) return;
    try {
      final markdown = await api.export(sessionId!);
      await Share.share(markdown, subject: 'Consultation 44 interprètes');
    } catch (exception) {
      setState(() => error = exception.toString());
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('44 interprètes'),
          actions: [
            DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: language,
                icon: const Icon(Icons.language),
                dropdownColor: const Color(0xff24152e),
                onChanged: busy ? null : _selectLanguage,
                items: languageLabels.entries.map((entry) => DropdownMenuItem(
                  value: entry.key,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: Text(entry.value),
                  ),
                )).toList(),
              ),
            ),
            IconButton(onPressed: _shareExport, icon: const Icon(Icons.ios_share), tooltip: tr('Exporter', 'Export')),
          ],
        ),
        body: SafeArea(child: _body()),
        bottomNavigationBar: NavigationBar(selectedIndex: tab, onDestinationSelected: (value) => setState(() => tab = value), destinations: [NavigationDestination(icon: const Icon(Icons.style), label: tr('Tapis', 'Spread')), NavigationDestination(icon: const Icon(Icons.chat_bubble_outline), label: 'Oracle'), NavigationDestination(icon: const Icon(Icons.info_outline), label: tr('À propos', 'About'))]),
      );

  Widget _body() {
    if (busy && session == null) return const Center(child: CircularProgressIndicator());
    if (tab == 1) return ChatView(messages: messages, busy: busy, onSend: _sendMessage);
    if (tab == 2) return const AboutView();
    return TapisView(cards: cards, faceDown: faceDown, faceUp: faceUp, busy: busy, error: error, onReveal: _reveal, onChat: () => setState(() => tab = 1));
  }
}

class TapisView extends StatelessWidget {
  const TapisView({super.key, required this.cards, required this.faceDown, required this.faceUp, required this.busy, required this.error, required this.onReveal, required this.onChat});
  final List<Map<String, dynamic>> cards;
  final List<Map<String, dynamic>> faceDown;
  final List<Map<String, dynamic>> faceUp;
  final bool busy;
  final String? error;
  final Future<void> Function(String) onReveal;
  final VoidCallback onChat;

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(16), children: [
        Text(tr('Le tapis', 'The spread'), style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Text(tr('Choisis une carte face cachée pour poursuivre la consultation.', 'Choose a face-down card to continue the consultation.'), style: const TextStyle(color: Colors.white70)),
        const SizedBox(height: 12),
        const Text(disclaimer, style: TextStyle(fontSize: 11, color: Colors.white54)),
        if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: const TextStyle(color: Colors.redAccent))),
        const SizedBox(height: 22),
        Wrap(alignment: WrapAlignment.center, spacing: 10, runSpacing: 12, children: faceDown.map((card) => _CardTile(card: card, onTap: busy ? null : () => onReveal(card['slot'] as String))).toList()),
        const SizedBox(height: 26),
        if (faceUp.isNotEmpty) Text(tr('Cartes révélées', 'Revealed cards'), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        ...faceUp.map((card) => ListTile(leading: const Icon(Icons.auto_awesome, color: Color(0xffd6ad62)), title: Text('${card['name']} (${card['code']})'), subtitle: Text('${card['slot']} · ${card['symbol'] ?? ''}'))),
        const SizedBox(height: 16),
        FilledButton.icon(onPressed: onChat, icon: const Icon(Icons.chat), label: Text(tr('Parler avec l’oracle', 'Talk to the oracle'))),
      ]);
}

class _CardTile extends StatelessWidget {
  const _CardTile({required this.card, required this.onTap});
  final Map<String, dynamic> card;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => InkWell(onTap: onTap, borderRadius: BorderRadius.circular(14), child: Container(width: 72, height: 108, decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), gradient: const LinearGradient(colors: [Color(0xff6e2346), Color(0xff30132e)]), border: Border.all(color: const Color(0xffd6ad62), width: 2), boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 10)]), child: Center(child: Text(card['slot'] as String, style: const TextStyle(color: Color(0xffe9cf8a), fontWeight: FontWeight.bold, fontSize: 16))));
}

class ChatView extends StatefulWidget {
  const ChatView({super.key, required this.messages, required this.busy, required this.onSend});
  final List<OracleMessage> messages;
  final bool busy;
  final Future<void> Function(String) onSend;
  @override
  State<ChatView> createState() => _ChatViewState();
}

class _ChatViewState extends State<ChatView> {
  final controller = TextEditingController();
  @override
  Widget build(BuildContext context) => Column(children: [Expanded(child: widget.messages.isEmpty ? Center(child: Text(tr('L’oracle vous écoute.', 'The oracle is listening.'))) : ListView.builder(padding: const EdgeInsets.all(16), itemCount: widget.messages.length, itemBuilder: (_, index) { final message = widget.messages[index]; return Align(alignment: message.role == 'user' ? Alignment.centerRight : Alignment.centerLeft, child: Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(14), constraints: const BoxConstraints(maxWidth: 360), decoration: BoxDecoration(color: message.role == 'user' ? const Color(0xff563a70) : const Color(0xff24152e), borderRadius: BorderRadius.circular(16)), child: Text(message.content))); })), if (widget.busy) const LinearProgressIndicator(), Padding(padding: const EdgeInsets.fromLTRB(12, 8, 12, 12), child: Row(children: [Expanded(child: TextField(controller: controller, minLines: 1, maxLines: 4, decoration: InputDecoration(hintText: tr('Écris à l’oracle…', 'Write to the oracle…'), border: const OutlineInputBorder()))), const SizedBox(width: 8), IconButton.filled(onPressed: widget.busy ? null : () { final text = controller.text; controller.clear(); widget.onSend(text); }, icon: const Icon(Icons.send))]))]);
  @override
  void dispose() { controller.dispose(); super.dispose(); }
}

class AboutView extends StatelessWidget {
  const AboutView({super.key});
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.all(24), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('44 interprètes', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)), const SizedBox(height: 16), Text(disclaimer), const SizedBox(height: 24), Text(tr('Les consultations sont anonymes et temporaires. Aucun compte ni historique persistant n’est requis.', 'Consultations are anonymous and temporary. No account or persistent history is required.'), style: const TextStyle(color: Colors.white70)), const SizedBox(height: 24), Text(tr('Soutenir l’hébergement', 'Support hosting'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)), const SizedBox(height: 8), Text(tr('Le lien de soutien PayPal sera ajouté avant la publication Play Store.', 'A PayPal support link will be added before Play Store publication.'), style: const TextStyle(color: Colors.white70))]));
}
