import 'package:flutter_test/flutter_test.dart';
import 'package:la_rosace/cards/hand_motion.dart';
import 'package:la_rosace/models/rosace_models.dart';

void main() {
  test('recall order sends outer cards first and keeps the three chosen', () {
    final placements = [
      CardPlacement(site: const RosaceSite(id: 0, kind: 'tip', x: 500, y: 108)),
      CardPlacement(site: const RosaceSite(id: 1, kind: 'cross', x: 500, y: 500)),
      CardPlacement(site: const RosaceSite(id: 2, kind: 'cross', x: 700, y: 300)),
      CardPlacement(site: const RosaceSite(id: 3, kind: 'tip', x: 108, y: 500)),
    ];
    final order = HandMotion.recallOrder(placements, const [1, 2]);
    expect(order, isNot(contains(1)));
    expect(order, isNot(contains(2)));
    expect(order.first, 0);
    expect(order, containsAll([0, 3]));
  });
}
