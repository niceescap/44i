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
    required this.dealSeq,
    required this.gatherSeq,
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
  final int gatherSeq;
  final bool busy;
  final String brandUrl;
  final Future<void> Function(int index) onReveal;
  final VoidCallback? onDealt;
  final VoidCallback? onGathered;

  @override
  State<RosaceStage> createState() => _RosaceStageState();
}

class _RosaceStageState extends State<RosaceStage> with TickerProviderStateMixin {
  late final AnimationController deal;
  late final AnimationController gather;
  late final AnimationController unveil;
  var _dealtSignaled = false;
  var _gatherSignaled = false;
  var _lastDealSeq = 0;
  var _lastGatherSeq = 0;

  static const _dealEase = Cubic(0.14, 0.82, 0.18, 1);
  static const _handEase = Cubic(0.16, 0.84, 0.18, 1);
  static const _recallEase = Cubic(0.18, 0.12, 0.2, 1);
  static const _unveilEase = Cubic(0.2, 0.8, 0.18, 1);

  bool get _oracle => widget.phase == 'oracle';
  bool get _recalling => widget.phase == 'recalling' || widget.gatherSeq > _lastGatherSeq || gather.value > 0 || unveil.value > 0;

  @override
  void initState() {
    super.initState();
    deal = AnimationController(vsync: this, duration: const Duration(milliseconds: HandMotion.dealMs))
      ..addStatusListener(_onDealStatus);
    gather = AnimationController(vsync: this, duration: const Duration(milliseconds: HandMotion.gatherMs))
      ..addStatusListener(_onGatherStatus);
    unveil = AnimationController(vsync: this, duration: const Duration(milliseconds: HandMotion.unveilMs))
      ..addStatusListener(_onUnveilStatus);
    _lastDealSeq = widget.dealSeq;
    _lastGatherSeq = widget.gatherSeq;
    if (widget.dealSeq > 0 && widget.phase == 'table') {
      deal.forward();
    } else if (_oracle) {
      deal.value = 1;
      gather.value = 1;
      unveil.value = 1;
    }
  }

  @override
  void didUpdateWidget(covariant RosaceStage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.dealSeq != _lastDealSeq) {
      _lastDealSeq = widget.dealSeq;
      _dealtSignaled = false;
      _gatherSignaled = false;
      gather
        ..stop()
        ..reset();
      unveil
        ..stop()
        ..reset();
      if (widget.dealSeq > 0 && widget.placements.isNotEmpty) {
        deal.forward(from: 0);
      } else {
        deal.reset();
      }
    }
    if (widget.gatherSeq != _lastGatherSeq && widget.gatherSeq > 0) {
      _lastGatherSeq = widget.gatherSeq;
      _gatherSignaled = false;
      deal.value = 1;
      unveil.reset();
      gather.forward(from: 0);
    }
    if (_oracle && gather.value == 0 && unveil.value == 0) {
      deal.value = 1;
      gather.value = 1;
      unveil.value = 1;
    }
  }

  void _onDealStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed) _signalDealt();
  }

  void _onGatherStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed && mounted) {
      unveil.forward(from: 0);
    }
  }

  void _onUnveilStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed) _signalGathered();
  }

  void _signalDealt() {
    if (_dealtSignaled) return;
    _dealtSignaled = true;
    widget.onDealt?.call();
  }

  void _signalGathered() {
    if (_gatherSignaled) return;
    _gatherSignaled = true;
    widget.onGathered?.call();
  }

  @override
  void dispose() {
    deal.removeStatusListener(_onDealStatus);
    gather.removeStatusListener(_onGatherStatus);
    unveil.removeStatusListener(_onUnveilStatus);
    deal.dispose();
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
            animation: Listenable.merge([deal, gather, unveil]),
            builder: (context, _) {
              if (widget.placements.isEmpty) {
                return const SizedBox.expand();
              }
              final dealRank = HandMotion.dealOrder(widget.placements);
              final returning = HandMotion.recallOrder(widget.placements, widget.chosen);
              final keep = widget.chosen.take(3).toList();
              final gathering = widget.phase == 'recalling' || widget.phase == 'oracle' || gather.value > 0 || unveil.value > 0;
              final order = gathering ? <int>[...returning, ...keep] : dealRank;
              final cloth = gathering ? (1 - gather.value).clamp(0.0, 1.0) : 1.0;
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
                    final pose = gathering
                        ? (handAt >= 0
                            ? _handPose(index, handAt, size, cardW, cardH)
                            : _recallPose(index, returning.indexOf(index), returning.length, size, cardW, cardH))
                        : _dealPose(index, dealRank.indexOf(index), dealRank.length, size, cardW, cardH);
                    if (pose.opacity <= 0.02) return const SizedBox.shrink();
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

  _CardPose _dealPose(int index, int rank, int n, double size, double cardW, double cardH) {
    final item = widget.placements[index];
    final dest = _site(item, size, cardW, cardH);
    final destRot = HandMotion.siteRot(item.site.id);
    if (deal.value >= 1) {
      return _CardPose(left: dest.dx, top: dest.dy, rot: destRot, scale: 1, opacity: 1);
    }
    final delay = (rank / (n <= 1 ? 1 : n - 1)) * HandMotion.dealStagger;
    final raw = ((deal.value * HandMotion.dealMs) - delay) / HandMotion.dealFlight;
    if (raw <= 0) {
      final spin = HandMotion.dealSpin(rank);
      return _CardPose(
        left: size / 2 - cardW / 2,
        top: size / 2 - cardH / 2,
        rot: spin,
        scale: 0.86,
        opacity: 1,
      );
    }
    final t = _dealEase.transform(raw.clamp(0.0, 1.0));
    final center = Offset(size / 2 - cardW / 2, size / 2 - cardH / 2);
    final spin = HandMotion.dealSpin(rank);
    if (t < 0.88) {
      final u = t / 0.88;
      final pos = Offset.lerp(center, dest, u)!;
      return _CardPose(
        left: pos.dx,
        top: pos.dy,
        rot: spin + (destRot * 0.55 - spin) * u,
        scale: 0.86 + (1.05 - 0.86) * u,
        opacity: 1,
      );
    }
    final u = (t - 0.88) / 0.12;
    return _CardPose(
      left: dest.dx,
      top: dest.dy,
      rot: destRot * 0.55 + (destRot - destRot * 0.55) * u,
      scale: 1.05 + (1 - 1.05) * u,
      opacity: 1,
    );
  }

  _CardPose _handPose(int index, int slot, double size, double cardW, double cardH) {
    final item = widget.placements[index];
    final from = _site(item, size, cardW, cardH);
    final fromRot = HandMotion.siteRot(item.site.id);
    final hand = HandMotion.handSlots[slot];
    final oracle = HandMotion.oracleSlots[slot];
    final handPos = Offset(hand.x * size - cardW / 2, hand.y * size - cardH / 2);
    final oraclePos = Offset(oracle.x * size - cardW / 2, oracle.y * size - cardH / 2);
    if (_oracle || unveil.value > 0 || gather.value >= 1) {
      final t = _oracle && unveil.value == 0 ? 1.0 : _unveilEase.transform(unveil.value.clamp(0.0, 1.0));
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
    if (t < 0.55) {
      final u = t / 0.55;
      final pos = Offset.lerp(from, handPos, u)!;
      return _CardPose(
        left: pos.dx,
        top: pos.dy,
        rot: fromRot + (midRot - fromRot) * u,
        scale: 1 + (1.42 - 1) * u,
        opacity: 1,
      );
    }
    final u = (t - 0.55) / 0.45;
    return _CardPose(
      left: handPos.dx,
      top: handPos.dy,
      rot: midRot + (hand.rot - midRot) * u,
      scale: 1.42 + (hand.scale - 1.42) * u,
      opacity: 1,
    );
  }

  _CardPose _recallPose(int index, int rank, int n, double size, double cardW, double cardH) {
    final item = widget.placements[index];
    final from = _site(item, size, cardW, cardH);
    final fromRot = HandMotion.siteRot(item.site.id);
    if (_oracle || gather.value >= 1) {
      return const _CardPose(left: 0, top: 0, rot: 0, scale: 0.5, opacity: 0);
    }
    if (rank < 0) {
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
