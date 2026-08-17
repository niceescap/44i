import 'package:flutter/material.dart';

import '../cards/hand_motion.dart';
import '../models/rosace_models.dart';
import '../theme.dart';
import 'playing_card.dart';

class RosaceStage extends StatefulWidget {
  const RosaceStage({
    super.key,
    required this.placements,
    required this.chosen,
    required this.phase,
    required this.busy,
    required this.brandUrl,
    required this.onReveal,
    this.onGathered,
  });

  final List<CardPlacement> placements;
  final List<int> chosen;
  final String phase;
  final bool busy;
  final String brandUrl;
  final Future<void> Function(int index) onReveal;
  final VoidCallback? onGathered;

  @override
  State<RosaceStage> createState() => _RosaceStageState();
}

class _RosaceStageState extends State<RosaceStage> with TickerProviderStateMixin {
  late final AnimationController gather;
  late final AnimationController unveil;
  var _signaled = false;

  static const _handEase = Cubic(0.16, 0.84, 0.18, 1);
  static const _recallEase = Cubic(0.18, 0.12, 0.2, 1);
  static const _unveilEase = Cubic(0.2, 0.8, 0.18, 1);

  @override
  void initState() {
    super.initState();
    gather = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: HandMotion.gatherMs),
    )..addStatusListener(_onGatherStatus);
    unveil = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: HandMotion.unveilMs),
    )..addStatusListener(_onUnveilStatus);
    if (widget.phase == 'recalling') {
      gather.forward();
    } else if (widget.phase == 'oracle') {
      gather.value = 1;
      unveil.value = 1;
    }
  }

  @override
  void didUpdateWidget(covariant RosaceStage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.phase == 'table' && oldWidget.phase != 'table') {
      _signaled = false;
      gather
        ..stop()
        ..reset();
      unveil
        ..stop()
        ..reset();
    } else if (widget.phase == 'recalling' && oldWidget.phase != 'recalling') {
      _signaled = false;
      unveil.reset();
      gather.forward(from: 0);
    }
  }

  void _onGatherStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed && mounted) {
      unveil.forward(from: 0);
    }
  }

  void _onUnveilStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed) _signalGathered();
  }

  void _signalGathered() {
    if (_signaled) return;
    _signaled = true;
    widget.onGathered?.call();
  }

  @override
  void dispose() {
    gather.removeStatusListener(_onGatherStatus);
    unveil.removeStatusListener(_onUnveilStatus);
    gather.dispose();
    unveil.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final size = constraints.biggest.shortestSide;
          final cardW = size * 0.072;
          final cardH = cardW * (49.5 / 34.5);
          return AnimatedBuilder(
            animation: Listenable.merge([gather, unveil]),
            builder: (context, _) {
              final returning = HandMotion.recallOrder(widget.placements, widget.chosen);
              final keep = widget.chosen.take(3).toList();
              final order = <int>[...returning, ...keep];
              final cloth = widget.phase == 'table' ? 1.0 : (1 - gather.value).clamp(0.0, 1.0);
              return Stack(
                clipBehavior: Clip.none,
                alignment: Alignment.center,
                children: [
                  Positioned.fill(
                    child: Opacity(
                      opacity: 0.28 * cloth,
                      child: Image.network(
                        widget.brandUrl,
                        fit: BoxFit.contain,
                        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                      ),
                    ),
                  ),
                  Positioned.fill(
                    child: Opacity(
                      opacity: cloth,
                      child: CustomPaint(painter: _StarPainter(widget.placements)),
                    ),
                  ),
                  ...order.map((index) {
                    if (index < 0 || index >= widget.placements.length) {
                      return const SizedBox.shrink();
                    }
                    final handAt = keep.indexOf(index);
                    final pose = handAt >= 0
                        ? _handPose(index, handAt, size, cardW, cardH)
                        : _recallPose(index, returning.indexOf(index), returning.length, size, cardW, cardH);
                    if (pose.opacity <= 0.01) return const SizedBox.shrink();
                    final item = widget.placements[index];
                    return Positioned(
                      left: pose.left,
                      top: pose.top,
                      child: Opacity(
                        opacity: pose.opacity,
                        child: Transform.rotate(
                          angle: pose.rot * 0.0174533,
                          child: Transform.scale(
                            scale: pose.scale,
                            child: PlayingCardView(
                              card: item.card,
                              revealed: item.revealed,
                              width: cardW,
                              height: cardH,
                              onTap: widget.busy || widget.phase != 'table' || item.revealed
                                  ? null
                                  : () => widget.onReveal(index),
                            ),
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              );
            },
          );
        },
      ),
    );
  }

  _CardPose _handPose(int index, int slot, double size, double cardW, double cardH) {
    final item = widget.placements[index];
    final from = _site(item, size, cardW, cardH);
    final fromRot = HandMotion.siteRot(item.site.id);
    if (widget.phase == 'table') {
      return _CardPose(left: from.dx, top: from.dy, rot: fromRot, scale: 1, opacity: 1);
    }
    final hand = HandMotion.handSlots[slot];
    final oracle = HandMotion.oracleSlots[slot];
    final handPos = Offset(hand.x * size - cardW / 2, hand.y * size - cardH / 2);
    final oraclePos = Offset(oracle.x * size - cardW / 2, oracle.y * size - cardH / 2);
    if (unveil.value > 0 || gather.value >= 1) {
      final t = _unveilEase.transform(unveil.value.clamp(0.0, 1.0));
      final pos = Offset.lerp(handPos, oraclePos, t)!;
      return _CardPose(
        left: pos.dx,
        top: pos.dy,
        rot: hand.rot + (oracle.rot - hand.rot) * t,
        scale: hand.scale + (oracle.scale - hand.scale) * t,
        opacity: 1,
      );
    }
    final raw = ((gather.value * HandMotion.gatherMs) - slot * HandMotion.handStagger) / HandMotion.handMs;
    final t = _handEase.transform(raw.clamp(0.0, 1.0));
    final midRot = hand.rot * 0.4;
    late final Offset pos;
    late final double rot;
    late final double scale;
    if (t < 0.55) {
      final u = t / 0.55;
      pos = Offset.lerp(from, handPos, u)!;
      rot = fromRot + (midRot - fromRot) * u;
      scale = 1 + (1.42 - 1) * u;
    } else {
      final u = (t - 0.55) / 0.45;
      pos = handPos;
      rot = midRot + (hand.rot - midRot) * u;
      scale = 1.42 + (hand.scale - 1.42) * u;
    }
    return _CardPose(left: pos.dx, top: pos.dy, rot: rot, scale: scale, opacity: 1);
  }

  _CardPose _recallPose(int index, int rank, int n, double size, double cardW, double cardH) {
    final item = widget.placements[index];
    final from = _site(item, size, cardW, cardH);
    final fromRot = HandMotion.siteRot(item.site.id);
    if (widget.phase == 'table' || rank < 0) {
      return _CardPose(left: from.dx, top: from.dy, rot: fromRot, scale: 1, opacity: 1);
    }
    final delay = (rank / (n <= 1 ? 1 : n - 1)) * HandMotion.recallStagger;
    final raw = ((gather.value * HandMotion.gatherMs) - delay) / HandMotion.recallFlight;
    final t = _recallEase.transform(raw.clamp(0.0, 1.0));
    final center = Offset(size / 2 - cardW / 2, size / 2 - cardH / 2);
    final spin = HandMotion.recallSpin(rank);
    if (t < 0.84) {
      final u = t / 0.84;
      final pos = Offset.lerp(from, center, u)!;
      return _CardPose(
        left: pos.dx,
        top: pos.dy,
        rot: fromRot + (spin - fromRot) * u,
        scale: 1 + (0.88 - 1) * u,
        opacity: 1,
      );
    }
    final u = (t - 0.84) / 0.16;
    return _CardPose(
      left: center.dx,
      top: center.dy,
      rot: spin,
      scale: 0.88 + (0.55 - 0.88) * u,
      opacity: 1 - u,
    );
  }

  Offset _site(CardPlacement item, double size, double cardW, double cardH) {
    return Offset(item.site.x / 1000 * size - cardW / 2, item.site.y / 1000 * size - cardH / 2);
  }
}

class _CardPose {
  const _CardPose({
    required this.left,
    required this.top,
    required this.rot,
    required this.scale,
    required this.opacity,
  });

  final double left;
  final double top;
  final double rot;
  final double scale;
  final double opacity;
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
