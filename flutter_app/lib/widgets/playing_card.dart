import 'package:flutter/material.dart';

import '../cards/deck.dart';
import '../theme.dart';

/// Dos + faces des cartes, asset-ready : utilise `assets/cards/<code>.png`
/// quand le fichier existe, sinon un placeholder vectoriel propre.
///
/// Jeu complet attendu (livré par l'éditeur) dans `flutter_app/assets/cards/` :
///   - `back.png` : dos
///   - `<code>.png` : une face par carte (ex. `6C.png`, `QH.png`, `AD.png`)
/// Les assets sont automatiquement pris en compte dès qu'ils sont présents,
/// pas de recompilation des visuels requis.
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
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xff12082a), Color(0xff2a1250)],
          ),
          border: Border.all(color: RosaceColors.gold, width: 1),
          boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 6)],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(5),
          child: revealed
              ? _asset('assets/cards/${card.code}.png', fallback: _FrontPlaceholder(card: card))
              : _asset('assets/cards/back.png', fallback: const _BackPlaceholder()),
        ),
      ),
    );
  }

  Widget _asset(String path, {required Widget fallback}) {
    return Image.asset(path, fit: BoxFit.fill, errorBuilder: (_, __, ___) => fallback);
  }
}

class _BackPlaceholder extends StatelessWidget {
  const _BackPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xff3b175b),
      alignment: Alignment.center,
      child: const Text(
        '✦',
        style: TextStyle(
          color: RosaceColors.gold,
          fontSize: 18,
          shadows: [Shadow(color: Colors.black45, blurRadius: 3)],
        ),
      ),
    );
  }
}

class _FrontPlaceholder extends StatelessWidget {
  const _FrontPlaceholder({required this.card});

  final PlayingCard card;

  @override
  Widget build(BuildContext context) {
    final color = card.red ? RosaceColors.red : RosaceColors.blackSuit;
    final face = PlayingCard.rankFace[card.rank] ?? card.rank;
    return ColoredBox(
      color: const Color(0xfff6edd4),
      child: Stack(
        children: [
          Positioned(
            left: 3,
            top: 2,
            child: Text(face, style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold, height: 1)),
          ),
          Positioned(
            left: 3,
            top: 11,
            child: Text(card.pip, style: TextStyle(color: color, fontSize: 8, height: 1)),
          ),
          Center(
            child: Text(
              card.pip,
              style: TextStyle(
                color: color,
                fontSize: 30,
                height: 1,
                shadows: const [Shadow(color: Colors.black26, blurRadius: 2)],
              ),
            ),
          ),
          Positioned(
            right: 3,
            bottom: 2,
            child: RotatedBox(quarterTurns: 2, child: Text('$face${card.pip}', style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold, height: 1))),
          ),
        ],
      ),
    );
  }
}