import '../models/rosace_models.dart';

class HandSlot {
  const HandSlot({
    required this.x,
    required this.y,
    required this.rot,
    required this.scale,
    required this.z,
  });

  final double x;
  final double y;
  final double rot;
  final double scale;
  final int z;
}

/// Constantes calquées sur rosace_depose.html (gatherToHand + unveilOracle).
class HandMotion {
  static const gatherMs = 3200;
  static const handMs = 1600;
  static const handStagger = 70;
  static const recallFlight = 2000;
  static const recallStagger = 1200;
  static const unveilMs = 900;
  static const fallbackMs = 5000;

  static const handSlots = [
    HandSlot(x: 0.452, y: 0.74, rot: -11, scale: 1.52, z: 260),
    HandSlot(x: 0.500, y: 0.73, rot: 2, scale: 1.52, z: 261),
    HandSlot(x: 0.548, y: 0.74, rot: 12, scale: 1.52, z: 262),
  ];

  static const oracleSlots = [
    HandSlot(x: 0.415, y: 0.54, rot: -10, scale: 2.15, z: 260),
    HandSlot(x: 0.500, y: 0.48, rot: 2, scale: 2.15, z: 261),
    HandSlot(x: 0.585, y: 0.54, rot: 12, scale: 2.15, z: 262),
  ];

  static double siteRot(int siteId) => ((siteId * 17) % 13) - 6.0;

  static double recallSpin(int rank) {
    final sign = rank.isOdd ? 1.0 : -1.0;
    return sign * (100 + (rank * 9) % 70);
  }

  static List<int> recallOrder(List<CardPlacement> placements, List<int> chosen) {
    final keep = chosen.take(3).toSet();
    final idxs = <int>[];
    for (var i = 0; i < placements.length; i++) {
      if (!keep.contains(i)) idxs.add(i);
    }
    idxs.sort((u, v) {
      final byR = placements[v].site.radius.compareTo(placements[u].site.radius);
      return byR != 0 ? byR : placements[u].site.angle.compareTo(placements[v].site.angle);
    });
    return idxs;
  }
}
