import 'package:flutter/material.dart';

import '../cards/deck.dart';
import '../theme.dart';

class PlayingCardView extends StatelessWidget {
  const PlayingCardView({
    super.key,
    required this.card,
    required this.revealed,
    this.onTap,
    this.width = 34,
    this.height = 49,
  });

  final PlayingCard card;
  final bool revealed;
  final VoidCallback? onTap;
  final double width;
  final double height;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 400),
        width: width,
        height: height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(4),
          gradient: revealed
              ? const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xfff6edd4), Color(0xffe4d2a4)],
                )
              : const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xff6e2346), Color(0xff30132e)],
                ),
          border: Border.all(color: RosaceColors.gold, width: 1),
          boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 4)],
        ),
        child: revealed ? _Front(card: card) : const _Back(),
      ),
    );
  }
}

class _Back extends StatelessWidget {
  const _Back();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text('✦', style: TextStyle(color: RosaceColors.gold.withOpacity(0.85), fontSize: 10)),
    );
  }
}

class _Front extends StatelessWidget {
  const _Front({required this.card});
  final PlayingCard card;

  @override
  Widget build(BuildContext context) {
    final color = card.red ? RosaceColors.red : RosaceColors.blackSuit;
    final face = PlayingCard.rankFace[card.rank] ?? card.rank;
    final layout = PlayingCard.pipLayout[card.rank];
    return Stack(
      children: [
        Positioned(left: 2, top: 1, child: _Corner(face: face, pip: card.pip, color: color)),
        Positioned(right: 2, bottom: 1, child: RotatedBox(quarterTurns: 2, child: _Corner(face: face, pip: card.pip, color: color))),
        if (layout != null)
          ...layout.map((pt) {
            final invert = pt.length > 2 && pt[2] == 1;
            return Positioned(
              left: (pt[0] / 100) * 34 - 5,
              top: (pt[1] / 100) * 49 - 6,
              child: Transform.rotate(
                angle: invert ? 3.1416 : 0,
                child: Text(card.pip, style: TextStyle(color: color, fontSize: card.rank == 'A' ? 14 : 8, height: 1)),
              ),
            );
          })
        else
          Center(
            child: Text('$face${card.pip}', style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 9)),
          ),
      ],
    );
  }
}

class _Corner extends StatelessWidget {
  const _Corner({required this.face, required this.pip, required this.color});
  final String face;
  final String pip;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(face, style: TextStyle(color: color, fontSize: 7, height: 1, fontWeight: FontWeight.bold)),
        Text(pip, style: TextStyle(color: color, fontSize: 7, height: 1)),
      ],
    );
  }
}
