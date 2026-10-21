import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:la_rosace/cards/revelation_guides.dart';

void main() {
  test('cardGuideLine uses CARD_MOTIF and 5 pre-recorded frames', () {
    final rng = Random(7);
    final seen = <String>{};
    for (var i = 0; i < 60; i++) {
      seen.add(RevelationGuides.cardGuideLine('6C', rng: rng));
    }
    expect(seen, isNotEmpty);
    // 'obstacles' est le motif de 6C ; la ligne le contient toujours.
    expect(seen.every((l) => l.contains('obstacles')), isTrue);
    expect(seen.every((l) => l.contains('trèfle')), isTrue);
    // ≤ 5 formulations distinctes possibles.
    expect(seen.length, lessThanOrEqualTo(5));
  });

  test('unknown code falls back to "un souffle"', () {
    expect(RevelationGuides.cardGuideLine('?X', rng: Random(1)), contains('un souffle'));
  });

  test('French card name is lowercase like the web', () {
    expect(RevelationGuides.frenchCardName('3H'), 'trois de cœur');
    expect(RevelationGuides.frenchCardName('QH'), 'dame de cœur');
    expect(RevelationGuides.frenchCardName('6C'), 'six de trèfle');
    expect(RevelationGuides.frenchCardName('AD'), 'as de carreau');
  });

  test('CARD_MOTIF covers the full 52 deck', () {
    const ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'];
    const suits = ['C', 'H', 'D', 'S'];
    var count = 0;
    for (final s in suits) {
      for (final r in ranks) {
        expect(RevelationGuides.CARD_MOTIF, contains('$r$s'), reason: '$r$s');
        count++;
      }
    }
    expect(count, 52);
  });
}