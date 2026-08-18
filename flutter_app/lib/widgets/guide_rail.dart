import 'package:flutter/material.dart';

import '../models/rosace_models.dart';

/// Bandeau de logs guides, hors bulles oracle.
class GuideRail extends StatelessWidget {
  const GuideRail({super.key, required this.guides});

  final List<ChatMessage> guides;

  @override
  Widget build(BuildContext context) {
    if (guides.isEmpty) return const SizedBox.shrink();
    final last = guides.length > 4 ? guides.sublist(guides.length - 4) : guides;
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(minHeight: 56),
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      decoration: BoxDecoration(
        color: const Color(0x66220e3a),
        border: Border(left: BorderSide(color: const Color(0xffc9a84c).withOpacity(0.7), width: 2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < last.length; i++)
            _GuideLine(text: last[i].content, pulse: i == last.length - 1 && last[i].pulse),
        ],
      ),
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
      style: const TextStyle(
        color: Color(0xffead7a6),
        fontSize: 13,
        height: 1.4,
        fontStyle: FontStyle.italic,
      ),
    );
    if (pulse == null) {
      return Padding(padding: const EdgeInsets.only(bottom: 4), child: text);
    }
    return AnimatedBuilder(
      animation: pulse!,
      builder: (context, _) {
        return Opacity(
          opacity: 0.4 + 0.6 * pulse!.value,
          child: Padding(padding: const EdgeInsets.only(bottom: 4), child: text),
        );
      },
    );
  }
}
