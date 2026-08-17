import 'dart:math' as math;

import '../cards/deck.dart';

class RosaceSite {
  const RosaceSite({
    required this.id,
    required this.kind,
    required this.x,
    required this.y,
  });

  final int id;
  final String kind;
  final double x;
  final double y;

  double get radius {
    final dx = (x - 500) / 392;
    final dy = (y - 500) / 392;
    return math.sqrt(dx * dx + dy * dy);
  }
  double get angle => math.atan2(y - 500, x - 500);

  factory RosaceSite.fromJson(Map<String, dynamic> json) => RosaceSite(
        id: json['id'] as int,
        kind: json['kind'] as String? ?? 'cross',
        x: (json['x'] as num).toDouble(),
        y: (json['y'] as num).toDouble(),
      );
}

class CardPlacement {
  CardPlacement({required this.site})
      : card = PlayingCard.unknown(),
        revealed = false;

  final RosaceSite site;
  PlayingCard card;
  bool revealed;
}

class ChatMessage {
  const ChatMessage({
    required this.role,
    required this.content,
    this.guide = false,
  });

  final String role;
  final String content;
  final bool guide;
}

class RosaceState {
  const RosaceState({
    required this.sessionId,
    required this.phase,
    required this.sites,
    required this.chosenCount,
    required this.locale,
  });

  final String sessionId;
  final String phase;
  final List<RosaceSite> sites;
  final int chosenCount;
  final String locale;

  factory RosaceState.fromJson(Map<String, dynamic> json) {
    final sites = ((json['sites'] as List?) ?? [])
        .map((item) => RosaceSite.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
    return RosaceState(
      sessionId: json['session_id'] as String? ?? '',
      phase: json['phase'] as String? ?? 'deal',
      sites: sites,
      chosenCount: json['chosen_count'] as int? ?? 0,
      locale: json['locale'] as String? ?? 'fr',
    );
  }
}
