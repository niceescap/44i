import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state/rosace_controller.dart';
import '../theme.dart';
import '../widgets/chat_panel.dart';
import '../widgets/rosace_stage.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final RosaceController controller;

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

  Future<void> _donate() async {
    await controller.track('don_click');
    final uri = Uri.parse('https://paypal.me/NiceeCap/2');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _privacy() async {
    final uri = Uri.parse('${controller.api.baseUrl}/privacy-policy');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
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
                child: Image.network(
                  _bandeauUrl,
                  fit: BoxFit.cover,
                  alignment: Alignment.topCenter,
                  errorBuilder: (_, __, ___) => const ColoredBox(color: RosaceColors.glow),
                ),
              ),
            ),
          ),
          SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
                  child: Column(
                    children: [
                      Text(s.title, style: rosaceTitleStyle(fontSize: 48)),
                      Text(s.tagline, style: const TextStyle(color: RosaceColors.tagline, fontStyle: FontStyle.italic)),
                      Text(s.subtitle, style: const TextStyle(color: RosaceColors.tagline, fontSize: 13)),
                    ],
                  ),
                ),
                if (controller.error != null)
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(controller.error!, style: const TextStyle(color: Colors.redAccent)),
                  ),
                Expanded(
                  flex: controller.phase == 'oracle' ? 4 : 6,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: RosaceStage(
                      placements: controller.placements,
                      phase: controller.phase,
                      busy: controller.dealing,
                      brandUrl: '${controller.api.baseUrl}/static/brand/rosace.png',
                      onReveal: controller.reveal,
                    ),
                  ),
                ),
                Expanded(
                  flex: controller.phase == 'oracle' ? 5 : 3,
                  child: ChatPanel(
                    messages: controller.messages,
                    ready: controller.chatReady,
                    busy: controller.dealing && controller.phase == 'oracle',
                    hint: s.writeHint,
                    audioLabel: s.listen,
                    premiumPuff: s.audioPremium,
                    onSend: controller.send,
                    onAudio: () => controller.track('audio_click'),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      FilledButton(onPressed: _premium, child: Text(s.premium)),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () {
                                controller.track('export');
                                Share.share(controller.exportMarkdown(), subject: 'La Rosace');
                              },
                              child: Text(s.keep),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton(
                              onPressed: controller.busy ? null : () => controller.deal(),
                              child: Text(s.again),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      OutlinedButton(onPressed: _donate, child: Text(s.donate)),
                      TextButton(
                        onPressed: _privacy,
                        child: Text(
                          '${s.legal} · ${s.privacy}',
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 10, color: RosaceColors.gold),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
