import 'package:flutter/material.dart';

import '../models/rosace_models.dart';
import '../theme.dart';
import 'playing_card.dart';

class RosaceStage extends StatelessWidget {
  const RosaceStage({
    super.key,
    required this.placements,
    required this.phase,
    required this.busy,
    required this.brandUrl,
    required this.onReveal,
  });

  final List<CardPlacement> placements;
  final String phase;
  final bool busy;
  final String brandUrl;
  final Future<void> Function(int index) onReveal;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final size = constraints.biggest.shortestSide;
          final cardW = size * 0.072;
          final cardH = cardW * (49.5 / 34.5);
          return Stack(
            alignment: Alignment.center,
            children: [
              Positioned.fill(
                child: Image.network(
                  brandUrl,
                  fit: BoxFit.contain,
                  opacity: const AlwaysStoppedAnimation(0.28),
                  errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                ),
              ),
              Positioned.fill(child: CustomPaint(painter: _StarPainter(placements))),
              ...placements.asMap().entries.map((entry) {
                final index = entry.key;
                final item = entry.value;
                final left = (item.site.x / 1000) * size - cardW / 2;
                final top = (item.site.y / 1000) * size - cardH / 2;
                final rot = ((item.site.id * 17) % 13) - 6;
                return Positioned(
                  left: left,
                  top: top,
                  child: Transform.rotate(
                    angle: rot * 0.0174533,
                    child: PlayingCardView(
                      card: item.card,
                      revealed: item.revealed,
                      width: cardW,
                      height: cardH,
                      onTap: busy || phase != 'table' || item.revealed ? null : () => onReveal(index),
                    ),
                  ),
                );
              }),
            ],
          );
        },
      ),
    );
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
