import 'package:flutter/material.dart';

import '../models/rosace_models.dart';

/// Bandeau de logs guides, hors bulles oracle. Compact et discret : les
/// dernières lignes, italiques, la dernière pulsant tant qu'elle est active.
class GuideRail extends StatelessWidget {
  const GuideRail({super.key, required this.guides, this.compact = false});

  final List<ChatMessage> guides;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (guides.isEmpty) return const SizedBox.shrink();
    final shown = guides.length > (compact ? 2 : 4)
        ? guides.sublist(guides.length - (compact ? 2 : 4))
        : guides;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(12, 0, 12, compact ? 2 : 8),
      padding: EdgeInsets.fromLTRB(12, compact ? 6 : 8, 12, compact ? 4 : 8),
      decoration: BoxDecoration(
        color: const Color(0x66220e3a),
        border: Border(
          left: BorderSide(color: const Color(0xffc9a84c).withOpacity(0.7), width: 2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < shown.length; i++)
            _GuideLine(text: shown[i].content, pulse: i == shown.length - 1 && shown[i].pulse, compact: compact),
        ],
      ),
    );
  }
}

class _GuideLine extends StatefulWidget {
  const _GuideLine({required this.text, required this.pulse, this.compact = false});
  final String text;
  final bool pulse;
  final bool compact;

  @override
  State<_GuideLine> createState() => _GuideLineState();
}

class _GuideLineState extends State<_GuideLine> with SingleTickerProviderStateMixin {
  AnimationController? pulse;

  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(covariant _GuideLine oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.pulse != widget.pulse) _sync();
  }

  void _sync() {
    if (widget.pulse) {
      pulse ??= AnimationController(vsync: this, duration: const Duration(milliseconds: 1600))
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
    final text = Text(
      widget.text,
      maxLines: widget.compact ? 2 : 3,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(
        color: const Color(0xffead7a6),
        fontSize: widget.compact ? 11 : 13,
        height: 1.35,
        fontStyle: FontStyle.italic,
      ),
    );
    if (pulse == null) {
      return Padding(padding: const EdgeInsets.only(bottom: 2), child: text);
    }
    return AnimatedBuilder(
      animation: pulse!,
      builder: (context, _) {
        return Opacity(
          opacity: 0.4 + 0.6 * pulse!.value,
          child: Padding(padding: const EdgeInsets.only(bottom: 2), child: text),
        );
      },
    );
  }
}