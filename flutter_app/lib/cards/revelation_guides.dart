import 'deck.dart';

/// Guides de révélation alignés sur rosace_depose.html
/// (cardGuideLine + appendDesignationFromEvent + appendContextLogs).
/// Source : data.symbolique / chosen[].event — pas de lexique local.
class RevelationGuides {
  static Map<String, dynamic> eventFromReveal(Map<String, dynamic> data, Map hit) {
    final fromHit = hit['event'];
    if (fromHit is Map && fromHit.isNotEmpty) {
      return Map<String, dynamic>.from(fromHit);
    }
    final rows = data['symbolique'];
    if (rows is List && rows.isNotEmpty && rows.last is Map) {
      return Map<String, dynamic>.from(rows.last as Map);
    }
    return {};
  }

  static String motif(Map<String, dynamic> ev) {
    final raw = '${ev['designation'] ?? ev['contenu'] ?? ''}'.trim();
    if (raw.isEmpty) return 'un souffle';
    return raw.split(',').first.trim();
  }

  static String cardName(PlayingCard card, Map<String, dynamic> ev) {
    final nom = '${ev['nom'] ?? ''}'.trim();
    return nom.isNotEmpty ? nom : card.frenchName;
  }

  static String cardLine({
    required PlayingCard card,
    required Map<String, dynamic> ev,
    required String Function(List<String>) pick,
  }) {
    final name = cardName(card, ev);
    final hint = motif(ev);
    final cap = name.isEmpty ? name : '${name[0].toUpperCase()}${name.substring(1)}';
    return pick([
      '$cap, $hint.',
      'Voici $name : $hint.',
      '$cap se montre, $hint.',
      'Tu lèves $name — $hint.',
      '$cap. Motif : $hint.',
    ]);
  }

  static List<String> contextLines(Map<String, dynamic> ev) {
    final lines = <String>[];
    final type = ev['type'];
    if (type == 'paire') {
      final names = _names(ev['cartes']);
      final body = '${ev['contenu_enrichi'] ?? ev['contenu'] ?? ''}'.trim();
      if (body.isNotEmpty) {
        lines.add(names.isEmpty ? 'Paire — $body' : 'Paire $names — $body');
      }
    } else if (type == 'apport') {
      final carte = _name(ev['carte']);
      final sur = _name(ev['sur']);
      final body = '${ev['contenu_enrichi'] ?? ev['conclusion'] ?? ''}'.trim();
      if (body.isNotEmpty) {
        lines.add('Apport $carte sur $sur — $body');
      }
    }
    final seen = <String>{};
    for (final rem in ev['remarquables'] as List? ?? const []) {
      if (rem is! Map) continue;
      final extra = '${rem['signification'] ?? rem['qualite'] ?? ''}'.trim();
      final cards = _names(rem['cartes']);
      final line =
          'Remarquable ${rem['sous_type'] ?? ''} $cards${extra.isEmpty ? '' : ' — $extra'}'
              .replaceAll(RegExp(r'\s+'), ' ')
              .trim();
      if (line.length > 'Remarquable'.length && seen.add(line)) {
        lines.add(line);
      }
    }
    return lines;
  }

  static String _name(Object? code) {
    final value = '$code'.trim();
    if (value.isEmpty) return '';
    return PlayingCard.fromCode(value).frenchName;
  }

  static String _names(Object? codes) {
    if (codes is! List) return '';
    return codes.map(_name).where((name) => name.isNotEmpty).join(' + ');
  }
}
