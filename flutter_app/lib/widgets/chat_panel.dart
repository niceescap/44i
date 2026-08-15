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
              final mine = message.role == 'user';
              return Align(
                alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
                  constraints: const BoxConstraints(maxWidth: 360),
                  decoration: BoxDecoration(
                    color: mine ? RosaceColors.bubbleUser : RosaceColors.bubbleOracle,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(message.content, style: TextStyle(color: RosaceColors.cream.withValues(alpha: 0.95), height: 1.35)),
                      if (!mine && !message.guide && message.content.isNotEmpty)
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
                            child: Text(puffIndex == index ? widget.premiumPuff : '🔊 ${widget.audioLabel}',
                                style: const TextStyle(color: RosaceColors.gold, fontSize: 12)),
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
