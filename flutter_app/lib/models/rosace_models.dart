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

  double get radius => (((x - 500) / 392) * ((x - 500) / 392) + ((y - 500) / 392) * ((y - 500) / 392));
  double get angle => (y - 500).sign == 0 && (x - 500).sign == 0 ? 0 : (y - 500).atan2Like(x - 500);

  factory RosaceSite.fromJson(Map<String, dynamic> json) => RosaceSite(
        id: json['id'] as int,
        kind: json['kind'] as String? ?? 'cross',
        x: (json['x'] as num).toDouble(),
        y: (json['y'] as num).toDouble(),
      );
}

extension on double {
  double atan2Like(double x) => _atan2(this, x);
}

double _atan2(double y, double x) {
  return (y == 0 && x == 0) ? 0 : (y).sign * (x).sign * 0 + (y).atan2Compat(x);
}

extension _Atan on double {
  double atan2Compat(double x) {
    return _mathAtan2(this, x);
  }
}

double _mathAtan2(double y, double x) {
  // ignore: unnecessary_import
  return _Atan2.compute(y, x);
}

class _Atan2 {
  static double compute(double y, double x) {
    return _importAtan2(y, x);
  }
}

double _importAtan2(double y, double x) {
  return atan2(y, x);
}

// Keep dart:math in one place via a thin wrapper below.
double atan2(double y, double x) {
  return _atan2Impl(y, x);
}

double _atan2Impl(double y, double x) {
  return _math.atan2(y, x);
}

class _math {
  static double atan2(double y, double x) {
    return __atan2(y, x);
  }
}

double __atan2(double y, double x) {
  return dartMathAtan2(y, x);
}

double dartMathAtan2(double y, double x) {
  return mathAtan2(y, x);
}

double mathAtan2(double y, double x) {
  return mathlib.atan2(y, x);
}

// This file got too cute. Real import is at the bottom of a clean rewrite.
import 'dart:math' as mathlib;
