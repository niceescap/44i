import 'package:flutter/material.dart';

import '../cards/hand_motion.dart';
import '../models/rosace_models.dart';
import '../theme.dart';
import 'playing_card.dart';

/// Tapis Flutter natif : on change les positions cibles, Flutter interpolé.
/// Pas de AnimationController (inopérant sur l’APK 1.2/1.3).
class RosaceStage extends StatefulWidget {
  const RosaceStage({
    super.key,
    required this.placements,
    required this.chosen,
    required this.phase,
    required this.dealSeq,
    required this.busy,
    required this.brandUrl,
    required this.onReveal,
    this.onDealt,
    this.onGathered,
  });

  final List<CardPlacement> placements;
  final List<int> chosen;
  final String phase;
  final int dealSeq;
  final bool busy;
  final String brandUrl;
  final Future<void> Function(int index) onReveal;
  final VoidCallback? onDealt;
  final VoidCallback? onGathered;

  @override
  State<RosaceStage> createState() => _RosaceStageState();
}

class _RosaceStageState extends State<RosaceStage> {
  var spread = false;
  var lastDeal = 0;
  var gatherArmed = false;

  bool get _hand => widget.phase == 'recalling' || widget.phase == 'oracle';

  @override
  void initState() {
    super.initState();
    lastDeal = widget.dealSeq;
    if (widget.placements.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() => spread = true);
      });
    }
  }

  @override
  void didUpdateWidget(covariant RosaceStage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.dealSeq != lastDeal) {
      lastDeal = widget.dealSeq;
      gatherArmed = false;
      spread = false;
      if (widget.placements.isNotEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          setState(() => spread = true);
          Future<void>.delayed(const Duration(milliseconds: 850), () {
            if (mounted) widget.onDealt?.call();
          });
        });
      }
    }
    if (widget.phase == 'recalling' && !gatherArmed) {
      gatherArmed = true;
      Future<void>.delayed(const Duration(milliseconds: 1100), () {
        if (mounted) widget.onGathered?.call();
      });
    }
    if (widget.phase == 'table') {
      gatherArmed = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final size = constraints.biggest.shortestSide;
          final cardW = size * 0.078;
          final cardH = cardW * (49.5 / 34.5);
          return Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned.fill(
                child: AnimatedOpacity(
                  duration: const Duration(milliseconds: 700),
                  opacity: _hand ? 0.08 : 0.28,
                  child: Image.asset(
                    'assets/brand/rosace.png',
                    fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) => Image.network(
                      widget.brandUrl,
                      fit: BoxFit.contain,
                      errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                    ),
                  ),
                ),
              ),
              Positioned.fill(
                child: AnimatedOpacity(
                  duration: const Duration(milliseconds: 700),
                  opacity: _hand ? 0.15 : 1,
                  child: CustomPaint(painter: _StarPainter(widget.placements)),
                ),
              ),
              ...List<Widget>.generate(widget.placements.length, (index) {
                return _placedCard(index, size, cardW, cardH);
              }),
            ],
          );
        },
      ),
    );
  }

  Widget _placedCard(int index, double size, double cardW, double cardH) {
    final item = widget.placements[index];
    final keepAt = widget.chosen.indexOf(index);
    final isKeep = keepAt >= 0 && keepAt < 3;
    final pose = _pose(item, keepAt, isKeep);
    return AnimatedPositioned(
      key: ValueKey('c-$index'),
      duration: Duration(milliseconds: _hand ? 900 : 780),
      curve: Curves.easeInOutCubic,
      left: pose[0] * size - cardW / 2,
      top: pose[1] * size - cardH / 2,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 650),
        opacity: pose[4],
        child: AnimatedRotation(
          duration: Duration(milliseconds: _hand ? 900 : 780),
          curve: Curves.easeInOutCubic,
          turns: pose[2] / 360,
          child: AnimatedScale(
            duration: Duration(milliseconds: _hand ? 900 : 780),
            curve: Curves.easeInOutCubic,
            scale: pose[3],
            child: PlayingCardView(
              card: item.card,
              revealed: item.revealed,
              width: cardW,
              height: cardH,
              onTap: widget.busy || widget.phase != 'table' || item.revealed || pose[4] < 0.5
                  ? null
                  : () => widget.onReveal(index),
            ),
          ),
        ),
      ),
    );
  }

  /// [x, y, rotDeg, scale, opacity] en fractions du tapis.
  List<double> _pose(CardPlacement item, int keepAt, bool isKeep) {
    if (_hand && isKeep) {
      const xs = [0.30, 0.50, 0.70];
      const rots = [-16.0, 2.0, 16.0];
      final oracle = widget.phase == 'oracle';
      return [xs[keepAt], oracle ? 0.48 : 0.64, rots[keepAt], oracle ? 2.15 : 1.75, 1];
    }
    if (_hand) {
      return [0.50, 0.50, 0, 0.35, 0];
    }
    if (!spread) {
      return [0.50, 0.50, HandMotion.siteRot(item.site.id), 0.82, 1];
    }
    return [item.site.x / 1000, item.site.y / 1000, HandMotion.siteRot(item.site.id), 1, 1];
  }
}

class _StarPainter extends CustomPainter {
  _StarPainter(this.placements);
  final List<CardPlacement> placements;

  @override
  void paint(Canvas canvas, Size size) {
    final tips = placements.where((item) => item.site.kind == 'tip').toList();
    if (tips.length < 13) return;
    Offset pt(CardPlacement item) => Offset(item.site.x / 1000 * size.width, item.site.y / 1000 * size.height);
    final gold = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = RosaceColors.gold.withOpacity(0.14);
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), size.width * 0.392, gold);
    final path = Path();
    for (var i = 0; i < 13; i++) {
      final p = pt(tips[i]);
      if (i == 0) {
        path.moveTo(p.dx, p.dy);
      } else {
        path.lineTo(p.dx, p.dy);
      }
    }
    path.close();
    canvas.drawPath(path, gold..color = RosaceColors.gold.withOpacity(0.08));
    final star = Path();
    for (var k = 0; k < 13; k++) {
      final a = pt(tips[k]);
      final b = pt(tips[(k + 4) % 13]);
      star.moveTo(a.dx, a.dy);
      star.lineTo(b.dx, b.dy);
    }
    canvas.drawPath(star, gold..color = RosaceColors.gold.withOpacity(0.05));
  }

  @override
  bool shouldRepaint(covariant _StarPainter oldDelegate) => oldDelegate.placements != placements;
}
