import 'package:flutter/material.dart';

import '../cards/deck.dart';
import '../theme.dart';

/// Carte à jouer : charge les PNG du deck La Rosace (propriété exclusive).
/// Fallback programmatique conservé pour robustesse.
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

  /// Mapping code carte → asset PNG.
  /// Convention : {A,K,Q,J,T,9,8,7,6,5,4,3,2}{C,D,H,S}.png + back.png
  String get _assetPath {
    if (!revealed || card.code == '?') return 'assets/cards/back.png';
    return 'assets/cards/${card.rank}${card.suit}.png';
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: RosaceColors.gold, width: 1),
          boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 4)],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: Image.asset(
            _assetPath,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => _Fallback(card: card, revealed: revealed),
          ),
        ),
      ),
    );
  }
}

/// Placeholder conservé en cas d'asset manquant (ne devrait pas arriver en prod).
class _Fallback extends StatelessWidget {
  const _Fallback({required this.card, required this.revealed});
  final PlayingCard card;
  final bool revealed;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
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
      ),
      child: revealed
          ? Center(
              child: Text(
                card.label,
                style: TextStyle(
                  color: card.red ? RosaceColors.red : RosaceColors.blackSuit,
                  fontWeight: FontWeight.bold,
                  fontSize: 9,
                ),
              ),
            )
          : Center(
              child: Text('✦', style: TextStyle(color: RosaceColors.gold.withOpacity(0.85), fontSize: 10)),
            ),
    );
  }
}
