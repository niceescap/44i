import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../cards/hand_motion.dart';
import '../models/rosace_models.dart';
import '../theme.dart';
import 'playing_card.dart';

/// Tapis Flutter natif : on change les positions cibles, Flutter interpole.
/// Pas de AnimationController (inopérant sur l'APK 1.2/1.3) : on séquence les
/// étapes (deal staggered, rappel staggered) avec des timers qui basculent
/// l'état de chaque carte. À la 3ᵉ carte, le rappel terminé, `onGathered`
/// déclenche le bascule page → mode ChatBox (les 3 cartes passent en main,
/// en-tête du chat). Constantes calquées sur rosace_depose.html.
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
  final List<Timer> _timers = [];
  final Set<int> _spread = {};
  final Set<int> _recalled = {};
  final Map<int, int> _dealRank = {};
  final Map<int, int> _recallRank = {};
  bool _recalling = false;
  int _lastDeal = 0;

  bool get _handPhase => widget.phase == 'recalling' || widget.phase == 'oracle';

  @override
  void initState() {
    super.initState();
    _lastDeal = widget.dealSeq;
    if (widget.placements.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _startDeal();
      });
    }
  }

  @override
  void didUpdateWidget(covariant RosaceStage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.dealSeq != _lastDeal) {
      _lastDeal = widget.dealSeq;
      _startDeal();
    }
    if (widget.phase == 'recalling' && !_recalling) {
      _recalling = true;
      _startRecall();
    }
    if (widget.phase == 'table' || widget.phase == 'oracle') {
      _recalling = false;
    }
  }

  @override
  void dispose() {
    for (final t in _timers) {
      t.cancel();
    }
    super.dispose();
  }

  void _after(Duration delay, void Function() action) {
    _timers.add(Timer(delay, action));
  }

  void _startDeal() {
    for (final t in _timers) {
      t.cancel();
    }
    _timers.clear();
    _spread.clear();
    _recalled.clear();
    _dealRank.clear();
    _recallRank.clear();
    _recalling = false;

    final order = HandMotion.dealOrder(widget.placements);
    final n = math.max(order.length - 1, 1);
    for (var rank = 0; rank < order.length; rank++) {
      _dealRank[order[rank]] = rank;
      final delay = Duration(milliseconds: (rank / n * HandMotion.dealStagger).round());
      _after(delay, () {
        if (mounted) setState(() => _spread.add(order[rank]));
      });
    }
    // Toutes les cartes posées → débloque les taps du tapis.
    _after(const Duration(milliseconds: HandMotion.dealMs), () {
      if (mounted) widget.onDealt?.call();
    });
  }

  void _startRecall() {
    for (final t in _timers) {
      t.cancel();
    }
    _timers.clear();
    _recalled.clear();

    final order = HandMotion.recallOrder(widget.placements, widget.chosen);
    final n = math.max(order.length - 1, 1);
    for (var rank = 0; rank < order.length; rank++) {
      _recallRank[order[rank]] = rank;
      final delay = Duration(milliseconds: (rank / n * HandMotion.recallStagger).round());
      _after(delay, () {
        if (mounted) setState(() => _recalled.add(order[rank]));
      });
    }
    // Rappel terminé → le tapis se replie, l'UI bascule en mode ChatBox
    // (les 3 cartes deviennent la main en tête de chat).
    _after(const Duration(milliseconds: HandMotion.gatherMs), () {
      if (mounted) widget.onGathered?.call();
    });
  }

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final size = constraints.biggest.shortestSide;
          final cardW = (size * 0.10).clamp(34.0, 58.0).toDouble();
          final cardH = cardW * (49.5 / 34.5);
          return Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned.fill(
                child: AnimatedOpacity(
                  duration: const Duration(milliseconds: 700),
                  opacity: _handPhase ? 0.08 : 0.28,
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
                  opacity: _handPhase ? 0.15 : 1,
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
    final pose = _pose(item, index, isKeep);
    final ms = _durationMs(isKeep);
    final curve = Curves.easeInOutCubic;
    return AnimatedPositioned(
      key: ValueKey('c-$index'),
      duration: Duration(milliseconds: ms),
      curve: curve,
      left: pose[0] * size - cardW / 2,
      top: pose[1] * size - cardH / 2,
      child: AnimatedOpacity(
        duration: Duration(milliseconds: ms),
        opacity: pose[4],
        child: AnimatedRotation(
          duration: Duration(milliseconds: ms),
          curve: curve,
          turns: pose[2] / 360,
          child: AnimatedScale(
            duration: Duration(milliseconds: ms),
            curve: curve,
            scale: pose[3],
            child: PlayingCardView(
              card: item.card,
              revealed: item.revealed,
              width: cardW,
              height: cardH,
              onTap: widget.busy ||
                      widget.phase != 'table' ||
                      item.revealed ||
                      !_spread.contains(index) ||
                      pose[4] < 0.5
                  ? null
                  : () => widget.onReveal(index),
            ),
          ),
        ),
      ),
    );
  }

  int _durationMs(bool isKeep) {
    if (widget.phase == 'recalling') {
      return isKeep ? HandMotion.recallFlight : HandMotion.recallFlight;
    }
    return HandMotion.dealFlight;
  }

  /// [x, y, rotDeg, scale, opacity] en fractions du tapis.
  List<double> _pose(CardPlacement item, int index, bool isKeep) {
    if (_handPhase) {
      // Les 3 choisies restent posées ; les autres rappellent au centre.
      if (isKeep) return _sitePose(item);
      if (!_recalled.contains(index)) return _sitePose(item);
      final rank = _recallRank[index] ?? 0;
      return [0.5, 0.5, HandMotion.recallSpin(rank), 0.55, 0];
    }
    if (!_spread.contains(index)) {
      final rank = _dealRank[index] ?? 0;
      return [0.5, 0.5, HandMotion.dealSpin(rank), 0.86, 1];
    }
    return _sitePose(item);
  }

  List<double> _sitePose(CardPlacement item) {
    return [
      item.site.x / 1000,
      item.site.y / 1000,
      HandMotion.siteRot(item.site.id),
      1,
      1,
    ];
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