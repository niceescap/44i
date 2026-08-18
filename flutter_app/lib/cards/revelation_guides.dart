import 'dart:math';

/// Guides de révélation alignés sur rosace_depose.html (workflow web validé).
///
/// Version compacte : mini-log court `cardGuideLine(code)` — « Nom, motif. » —
/// parmi 5 formulations pré-enregistrées tirées au sort. **Aucun** paragraphe
/// verbeux (Paire / Apport / Remarquable) dans le chat : ces détails restent
/// côté serveur (logs techniques), comme sur le web servi en ligne.
class RevelationGuides {
  /// Motif par carte, identique à `CARD_MOTIF` de rosace_depose.html.
  static const Map<String, String> CARD_MOTIF = {
    'AC': 'triomphe', 'KC': 'homme protecteur', 'QC': 'femme alliée', 'JC': 'jeune homme', 'TC': 'argent',
    '9C': 'travail', '8C': 'association', '7C': 'l’esprit', '6C': 'obstacles', '5C': 'implication',
    '4C': 'imprudence', '3C': 'soutien', '2C': 'hésitation',
    'AH': 'le foyer', 'KH': 'homme bienveillant', 'QH': 'femme bienveillante', 'JH': 'rencontre légère', 'TH': 'vie sociale',
    '9H': 'accomplissement', '8H': 'sentiments', '7H': 'vie affective', '6H': 'souvenirs', '5H': 'échanges du cœur',
    '4H': 'déception', '3H': 'union', '2H': 'malentendu',
    'AD': 'une nouvelle', 'KD': 'autorité lointaine', 'QD': 'jalousie', 'JD': 'le message', 'TD': 'le voyage',
    '9D': 'le retard', '8D': 'une démarche', '7D': 'discussion vive', '6D': 'petit flux d’argent', '5D': 'vie cachée',
    '4D': 'concrétisation', '3D': 'construction', '2D': 'indécision',
    'AS': 'les papiers', 'KS': 'figure officielle', 'QS': 'solitude', 'JS': 'avertissement', 'TS': 'nuages',
    '9S': 'coup du sort', '8S': 'ragots', '7S': 'lutte', '6S': 'petits accrocs', '5S': 'rupture',
    '4S': 'retrait', '3S': 'rivalité', '2S': 'tromperie',
  };

  static const Map<String, String> _rankFr = {
    'A': 'as', '2': 'deux', '3': 'trois', '4': 'quatre', '5': 'cinq', '6': 'six',
    '7': 'sept', '8': 'huit', '9': 'neuf', 'T': 'dix', 'J': 'valet', 'Q': 'dame', 'K': 'roi',
  };
  static const Map<String, String> _suitFr = {
    'S': 'pique', 'H': 'cœur', 'D': 'carreau', 'C': 'trèfle',
  };

  /// Nom français du code, minuscules comme sur le web (« six de trèfle »).
  static String frenchCardName(String code) {
    if (code.length < 2) return code;
    final rank = code.substring(0, code.length - 1);
    final suit = code.substring(code.length - 1);
    return '${_rankFr[rank] ?? rank} de ${_suitFr[suit] ?? suit}';
  }

  /// Mini-log web : « Six de trèfle, obstacles. » — 5 formulations tirées au sort.
  static String cardGuideLine(String code, {Random? rng}) {
    final name = frenchCardName(code);
    final motif = CARD_MOTIF[code] ?? 'un souffle';
    final cap = name.isEmpty ? name : '${name[0].toUpperCase()}${name.substring(1)}';
    final frames = [
      '$cap, $motif.',
      'Voici $name : $motif.',
      '$cap se montre, $motif.',
      'Tu lèves $name — $motif.',
      '$cap. Motif : $motif.',
    ];
    return frames[(rng ?? Random()).nextInt(frames.length)];
  }
}