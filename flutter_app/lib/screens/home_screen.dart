import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../cards/deck.dart';
import '../l10n/app_strings.dart';
import '../models/rosace_models.dart';
import '../state/rosace_controller.dart';
import '../theme.dart';
import '../widgets/chat_panel.dart';
import '../widgets/guide_rail.dart';
import '../widgets/hand_header.dart';
import '../widgets/rosace_stage.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final RosaceController controller;

  bool get _chatMode => controller.phase == 'oracle';

  @override
  void initState() {
    super.initState();
    controller = RosaceController();
    controller.addListener(_refresh);
    controller.start();
  }

  void _refresh() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    controller
      ..removeListener(_refresh)
      ..dispose();
    super.dispose();
  }

  String get _bandeauUrl => '${controller.api.baseUrl}/static/brand/bandeau.jpg';
  String get _brandUrl => '${controller.api.baseUrl}/static/brand/rosace.png';

  List<PlayingCard> get _handCards {
    final cards = <PlayingCard>[];
    for (final idx in controller.chosen.take(3)) {
      if (idx >= 0 && idx < controller.placements.length && controller.placements[idx].revealed) {
        cards.add(controller.placements[idx].card);
      }
    }
    return cards;
  }

  List<ChatMessage> get _guides => controller.messages.where((m) => m.guide).toList();

  Future<void> _privacy() async {
    final uri = Uri.parse('${controller.api.baseUrl}/privacy-policy');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  void _export() {
    controller.track('export');
    Share.share(controller.exportMarkdown(), subject: 'La Rosace');
  }

  Future<void> _premium() async {
    await controller.track('premium_click');
    if (!mounted) return;
    final emailController = TextEditingController();
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: RosaceColors.felt,
      builder: (context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(20, 16, 20, 16 + MediaQuery.of(context).viewInsets.bottom),
          child: StatefulBuilder(
            builder: (context, setModal) => Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(controller.strings.premiumTitle, style: const TextStyle(fontSize: 24, color: RosaceColors.cream)),
                const SizedBox(height: 12),
                Text(controller.strings.premiumBody),
                const SizedBox(height: 16),
                if (!controller.premiumThanks) ...[
                  TextField(
                    controller: emailController,
                    keyboardType: TextInputType.emailAddress,
                    decoration: InputDecoration(hintText: controller.strings.emailHint),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: () async {
                      final email = emailController.text.trim();
                      if (email.isEmpty) return;
                      try {
                        await controller.track('premium_email', email: email);
                        controller.premiumThanks = true;
                        setModal(() {});
                      } catch (_) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(controller.strings.silent)));
                        }
                      }
                    },
                    child: Text(controller.strings.notifyMe),
                  ),
                ] else
                  Text(controller.strings.thanks, style: const TextStyle(color: RosaceColors.gold, fontStyle: FontStyle.italic)),
                TextButton(onPressed: () => Navigator.pop(context), child: Text(controller.strings.close)),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = controller.strings;
    return Scaffold(
      body: Stack(
        children: [
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: 280,
            child: IgnorePointer(
              child: Opacity(
                opacity: RosaceColors.bandeauOpacity,
                child: Image.asset(
                  'assets/brand/bandeau.jpg',
                  fit: BoxFit.cover,
                  alignment: Alignment.topCenter,
                  errorBuilder: (_, __, ___) => Image.network(
                    _bandeauUrl,
                    fit: BoxFit.cover,
                    alignment: Alignment.topCenter,
                    errorBuilder: (_, __, ___) => const ColoredBox(color: RosaceColors.glow),
                  ),
                ),
              ),
            ),
          ),
          SafeArea(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 600),
              switchInCurve: Curves.easeInOut,
              switchOutCurve: Curves.easeIn,
              transitionBuilder: (child, anim) => FadeTransition(
                opacity: anim,
                child: ScaleTransition(
                  scale: Tween(begin: 0.985, end: 1.0).animate(anim),
                  child: child,
                ),
              ),
              child: _chatMode ? _chatScene(s) : _tapisScene(s),
            ),
          ),
        ],
      ),
    );
  }

  Widget _header(AppStrings s, {required bool chat}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
      child: Column(
        children: [
          Text(s.title, style: rosaceTitleStyle(fontSize: chat ? 26 : 38), textAlign: TextAlign.center),
          const SizedBox(height: 2),
          Text(
            '${appVersionLabel} · ${s.subtitle}',
            style: const TextStyle(color: RosaceColors.tagline, fontSize: 11, fontStyle: FontStyle.italic),
          ),
        ],
      ),
    );
  }

  Widget _tapisScene(AppStrings s) {
    return Column(
      key: const ValueKey('tapis'),
      children: [
        _header(s, chat: false),
        if (controller.error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(controller.error!, style: const TextStyle(color: Colors.redAccent)),
          ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
            children: [
              RosaceStage(
                key: const ValueKey('rosace-stage'),
                placements: controller.placements,
                chosen: List<int>.from(controller.chosen),
                phase: controller.phase,
                dealSeq: controller.dealSeq,
                busy: controller.dealing,
                brandUrl: _brandUrl,
                onReveal: controller.reveal,
                onDealt: controller.finishDeal,
                onGathered: controller.beginOracle,
              ),
              const SizedBox(height: 6),
              if (_guides.isNotEmpty) GuideRail(guides: _guides),
            ],
          ),
        ),
        _toolbar(s),
      ],
    );
  }

  Widget _chatScene(AppStrings s) {
    return Column(
      key: const ValueKey('chat'),
      children: [
        _header(s, chat: true),
        HandHeader(cards: _handCards),
        if (_guides.isNotEmpty) GuideRail(guides: _guides, compact: true),
        Expanded(
          child: ChatPanel(
            messages: controller.messages.where((m) => !m.guide).toList(),
            ready: controller.chatReady,
            busy: controller.dealing && controller.phase == 'oracle',
            hint: s.writeHint,
            audioLabel: s.listen,
            premiumPuff: s.audioPremium,
            onSend: controller.send,
            onAudio: () => controller.track('audio_click'),
          ),
        ),
        _toolbar(s),
      ],
    );
  }

  Widget _toolbar(AppStrings s) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 2, 10, 8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 4),
          decoration: BoxDecoration(
            color: RosaceColors.ink.withOpacity(0.62),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: RosaceColors.gold.withOpacity(0.5)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _tool(Icons.replay, s.again, controller.busy ? null : () => controller.deal()),
              _tool(Icons.ios_share, s.keep, _export),
              _tool(Icons.favorite, s.donate, _donate),
              _tool(Icons.workspace_premium, s.premium, _premium),
            ],
          ),
        ),
      ),
    );
  }

  Widget _tool(IconData icon, String label, VoidCallback? onTap) {
    return Tooltip(
      message: label,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: onTap == null ? Colors.white24 : RosaceColors.gold, size: 22),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(color: onTap == null ? Colors.white24 : RosaceColors.tagline, fontSize: 9),
              ),
            ],
          ),
        ),
      ),
    );
  }
}