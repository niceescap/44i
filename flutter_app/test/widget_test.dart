import 'package:flutter_test/flutter_test.dart';

import 'package:interpretes44/cards/deck.dart';

void main() {
  test('French card names follow the web lexicon', () {
    final club = PlayingCard.fromCode('6C');
    expect(club.frenchName, 'Six de Trèfle');
    expect(club.red, isFalse);
    final heart = PlayingCard.fromCode('QH');
    expect(heart.frenchName, 'Dame de Cœur');
    expect(heart.red, isTrue);
  });
}
