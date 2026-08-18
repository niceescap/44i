import 'package:flutter_test/flutter_test.dart';
import 'package:la_rosace/cards/deck.dart';
import 'package:la_rosace/cards/revelation_guides.dart';

void main() {
  test('motif takes the first clause of designation', () {
    expect(
      RevelationGuides.motif({
        'designation': 'union, accord, mariage possible',
      }),
      'union',
    );
    expect(RevelationGuides.motif({}), 'un souffle');
  });

  test('card line uses French name and motif from symbolique', () {
    final card = PlayingCard.fromCode('3H');
    final line = RevelationGuides.cardLine(
      card: card,
      ev: {'nom': 'Trois de Cœur', 'designation': 'union, accord'},
      pick: (frames) => frames[1],
    );
    expect(line, 'Voici Trois de Cœur : union.');
  });

  test('paire and apport lines use French names', () {
    final pair = RevelationGuides.contextLines({
      'type': 'paire',
      'cartes': ['3S', '3H'],
      'contenu_enrichi': 'union — lecture de paire',
    });
    expect(pair.single, 'Paire Trois de Pique + Trois de Cœur — union — lecture de paire');

    final apport = RevelationGuides.contextLines({
      'type': 'apport',
      'carte': 'TC',
      'sur': '3H',
      'contenu_enrichi': 'argent — harmonie',
    });
    expect(apport.single, 'Apport Dix de Trèfle sur Trois de Cœur — argent — harmonie');
  });

  test('event prefers chosen[].event then last symbolique row', () {
    final fromHit = RevelationGuides.eventFromReveal(
      {
        'symbolique': [
          {'type': 'designation', 'carte': '3S'},
        ],
      },
      {
        'event': {'type': 'paire', 'cartes': ['3S', '3H']},
      },
    );
    expect(fromHit['type'], 'paire');

    final fromSnap = RevelationGuides.eventFromReveal(
      {
        'symbolique': [
          {'type': 'designation', 'carte': '3S'},
        ],
      },
      {},
    );
    expect(fromSnap['carte'], '3S');
  });
}
