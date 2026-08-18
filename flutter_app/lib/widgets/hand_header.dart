import 'package:flutter/material.dart';

import '../cards/deck.dart';
import 'playing_card.dart';

/// Main de 3 cartes, en-tête du mode ChatBox : les trois cartes tirées,
/// harmonieusement disposées en éventail, devenues le support de la lecture.
class HandHeader extends StatelessWidget {
  const HandHeader({super.key, required this.cards});

  final List<PlayingCard> cards;

  static const _rots = [-0.16, 0.0, 0.16];

  @override
  Widget build(BuildContext context) {
    if (cards.isEmpty) return const SizedBox(height: 110);
    return Container(
      height: 122,
      width: double.infinity,
      alignment: Alignment.bottomCenter,
      padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (var i = 0; i < cards.length; i++)
            Padding(
              padding: EdgeInsets.symmetric(horizontal: i == 1 ? 2 : 8),
              child: Transform.rotate(
                angle: _rots[i],
                child: PlayingCardView(card: cards[i], revealed: true, width: 64, height: 92),
              ),
            ),
        ],
      ),
    );
  }
}