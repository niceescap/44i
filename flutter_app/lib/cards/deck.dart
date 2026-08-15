class PlayingCard {
  const PlayingCard({
    required this.code,
    required this.rank,
    required this.suit,
    required this.pip,
    required this.red,
    required this.label,
    required this.frenchName,
  });

  final String code;
  final String rank;
  final String suit;
  final String pip;
  final bool red;
  final String label;
  final String frenchName;

  static const ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'];
  static const rankFace = {
    'A': 'A',
    'T': '10',
    'J': 'V',
    'Q': 'D',
    'K': 'R',
  };
  static const rankFr = {
    'A': 'As',
    '2': 'Deux',
    '3': 'Trois',
    '4': 'Quatre',
    '5': 'Cinq',
    '6': 'Six',
    '7': 'Sept',
    '8': 'Huit',
    '9': 'Neuf',
    'T': 'Dix',
    'J': 'Valet',
    'Q': 'Dame',
    'K': 'Roi',
  };
  static const suitFr = {'S': 'Pique', 'H': 'Cœur', 'D': 'Carreau', 'C': 'Trèfle'};
  static const suitPip = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'};
  static const pipLayout = <String, List<List<double>>>{
    'A': [
      [50, 52],
    ],
    '2': [
      [50, 22],
      [50, 78, 1],
    ],
    '3': [
      [50, 20],
      [50, 50],
      [50, 80, 1],
    ],
    '4': [
      [30, 22],
      [70, 22],
      [30, 78, 1],
      [70, 78, 1],
    ],
    '5': [
      [30, 22],
      [70, 22],
      [50, 50],
      [30, 78, 1],
      [70, 78, 1],
    ],
    '6': [
      [30, 22],
      [70, 22],
      [30, 50],
      [70, 50],
      [30, 78, 1],
      [70, 78, 1],
    ],
    '7': [
      [30, 20],
      [70, 20],
      [50, 36],
      [30, 50],
      [70, 50],
      [30, 80, 1],
      [70, 80, 1],
    ],
    '8': [
      [30, 20],
      [70, 20],
      [50, 34],
      [30, 50],
      [70, 50],
      [50, 66, 1],
      [30, 80, 1],
      [70, 80, 1],
    ],
    '9': [
      [30, 18],
      [70, 18],
      [30, 38],
      [70, 38],
      [50, 50],
      [30, 62, 1],
      [70, 62, 1],
      [30, 82, 1],
      [70, 82, 1],
    ],
    'T': [
      [30, 16],
      [70, 16],
      [50, 25],
      [30, 34],
      [70, 34],
      [30, 66, 1],
      [70, 66, 1],
      [50, 75, 1],
      [30, 84, 1],
      [70, 84, 1],
    ],
  };

  static PlayingCard unknown() => const PlayingCard(
        code: '?',
        rank: '?',
        suit: '?',
        pip: '✦',
        red: false,
        label: '✦',
        frenchName: 'Face cachée',
      );

  static PlayingCard fromCode(String code) {
    if (code.length < 2) return unknown();
    final rank = code.substring(0, code.length - 1);
    final suit = code.substring(code.length - 1);
    final pip = suitPip[suit] ?? '✦';
    final face = rankFace[rank] ?? rank;
    final name = '${rankFr[rank] ?? rank} de ${suitFr[suit] ?? suit}';
    return PlayingCard(
      code: code,
      rank: rank,
      suit: suit,
      pip: pip,
      red: suit == 'H' || suit == 'D',
      label: '$face$pip',
      frenchName: name,
    );
  }
}
