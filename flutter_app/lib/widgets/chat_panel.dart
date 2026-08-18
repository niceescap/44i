import 'package:flutter/material.dart';

import '../models/rosace_models.dart';
import '../theme.dart';

class ChatPanel extends StatefulWidget {
  const ChatPanel({
    super.key,
    required this.messages,
    required this.ready,
    required this.busy,
    required this.hint,
    required this.audioLabel,
    required this.premiumPuff,
    required this.onSend,
    required this.onAudio,
  });

  final List<ChatMessage> messages;
  final bool ready;
  final bool busy;
  final String hint;
  final String audioLabel;
  final String premiumPuff;
  final Future<void> Function(String) onSend;
  final VoidCallback onAudio;

  @override
  State<ChatPanel> createState() => _ChatPanelState();
}

class _ChatPanelState extends State<ChatPanel> {
  final controller = TextEditingController();
  final scroll = ScrollController();
  int? puffIndex;

  @override
  void didUpdateWidget(covariant ChatPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.messages.length != oldWidget.messages.length ||
        (widget.messages.isNotEmpty &&
            oldWidget.messages.isNotEmpty &&
            widget.messages.last.content != oldWidget.messages.last.content)) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!scroll.hasClients) return;
        scroll.animateTo(scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 240), curve: Curves.easeOut);
      });
    }
  }

  @override
  void dispose() {
    controller.dispose();
    scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            controller: scroll,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            itemCount: widget.messages.length,
            itemBuilder: (context, index) {
              final message = widget.messages[index];
              if (message.guide) {
                return _GuideLine(text: message.content, pulse: message.pulse);
              }
              final mine = message.role == 'user';
              final waiting = !mine && message.content.isEmpty;
              return Align(
                alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
                child: waiting
                    ? const Padding(
                        padding: EdgeInsets.only(bottom: 10, left: 4),
                        child: _WaitMark(),
                      )
                    : Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.fromLTRB(13, 10, 13, 10),
                        constraints: const BoxConstraints(maxWidth: 360),
                        decoration: BoxDecoration(
                          color: mine ? RosaceColors.bubbleUser.withOpacity(0.72) : RosaceColors.bubbleOracle.withOpacity(0.72),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              message.content,
                              style: TextStyle(
                                color: RosaceColors.cream.withOpacity(0.96),
                                height: 1.45,
                                fontSize: 15,
                              ),
                            ),
                            if (!mine)
                              Align(
                                alignment: Alignment.centerRight,
                                child: TextButton(
                                  onPressed: () {
                                    widget.onAudio();
                                    setState(() => puffIndex = index);
                                    Future<void>.delayed(const Duration(milliseconds: 1400), () {
                                      if (mounted && puffIndex == index) setState(() => puffIndex = null);
                                    });
                                  },
                                  child: Text(
                                    puffIndex == index ? widget.premiumPuff : '🔊 ${widget.audioLabel}',
                                    style: const TextStyle(color: RosaceColors.gold, fontSize: 12),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
              );
            },
          ),
        ),
        if (widget.busy) const LinearProgressIndicator(minHeight: 2, color: RosaceColors.gold),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: controller,
                  enabled: widget.ready,
                  minLines: 1,
                  maxLines: 4,
                  maxLength: 500,
                  decoration: InputDecoration(
                    counterText: '',
                    hintText: widget.hint,
                    border: const OutlineInputBorder(),
                  ),
                  onSubmitted: widget.ready && !widget.busy
                      ? (value) {
                          controller.clear();
                          widget.onSend(value);
                        }
                      : null,
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                onPressed: !widget.ready || widget.busy
                    ? null
                    : () {
                        final text = controller.text;
                        controller.clear();
                        widget.onSend(text);
                      },
                icon: const Icon(Icons.send),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _GuideLine extends StatefulWidget {
  const _GuideLine({required this.text, required this.pulse});
  final String text;
  final bool pulse;

  @override
  State<_GuideLine> createState() => _GuideLineState();
}

class _GuideLineState extends State<_GuideLine> with SingleTickerProviderStateMixin {
  AnimationController? pulse;

  @override
  void initState() {
    super.initState();
    _syncPulse();
  }

  @override
  void didUpdateWidget(covariant _GuideLine oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.pulse != widget.pulse) _syncPulse();
  }

  void _syncPulse() {
    if (widget.pulse) {
      pulse ??= AnimationController(vsync: this, duration: const Duration(milliseconds: 1700))
        ..repeat(reverse: true);
    } else {
      pulse?.dispose();
      pulse = null;
    }
  }

  @override
  void dispose() {
    pulse?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
      color: const Color(0xffead7a6),
      fontSize: 12,
      height: 1.45,
      fontStyle: FontStyle.italic,
      shadows: const [Shadow(color: Color(0xa6120620), blurRadius: 10)],
    );
    final child = Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(widget.text, style: style),
    );
    if (pulse == null) return child;
    return AnimatedBuilder(
      animation: pulse!,
      builder: (context, _) {
        return Opacity(opacity: 0.38 + 0.62 * pulse!.value, child: child);
      },
    );
  }
}

class _WaitMark extends StatefulWidget {
  const _WaitMark();

  @override
  State<_WaitMark> createState() => _WaitMarkState();
}

class _WaitMarkState extends State<_WaitMark> with SingleTickerProviderStateMixin {
  late final AnimationController pulse;

  @override
  void initState() {
    super.initState();
    pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 1150))..repeat(reverse: true);
  }

  @override
  void dispose() {
    pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: pulse,
      builder: (context, _) {
        return Opacity(
          opacity: 0.38 + 0.62 * pulse.value,
          child: Container(
            width: 18,
            height: 18,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: RosaceColors.gold.withOpacity(0.55)),
              boxShadow: [BoxShadow(color: RosaceColors.gold.withOpacity(0.18), blurRadius: 10)],
            ),
          ),
        );
      },
    );
  }
}
