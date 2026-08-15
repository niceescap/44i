import 'package:flutter/material.dart';

class RosaceColors {
  static const ink = Color(0xff0a0510);
  static const felt = Color(0xff1a0e24);
  static const gold = Color(0xffc9a84c);
  static const cream = Color(0xfff6edd4);
  static const red = Color(0xffb41c32);
  static const blackSuit = Color(0xff1a1a2e);
  static const bubbleOracle = Color(0xff24152e);
  static const bubbleUser = Color(0xff563a70);
}

ThemeData rosaceTheme() {
  return ThemeData(
    brightness: Brightness.dark,
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: RosaceColors.gold,
      brightness: Brightness.dark,
    ),
    scaffoldBackgroundColor: RosaceColors.ink,
    fontFamily: 'serif',
  );
}
