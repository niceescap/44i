import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Palette alignée sur le web validé (pourpre 20 % plus sombre).
class RosaceColors {
  static const felt = Color(0xff2e134d);
  static const ink = Color(0xff220e3a);
  static const glow = Color(0xff3b175b);
  static const gold = Color(0xffc9a84c);
  static const cream = Color(0xfff6edd4);
  static const tagline = Color(0xffd2be86);
  static const red = Color(0xffb41c32);
  static const blackSuit = Color(0xff1a1a2e);
  static const bubbleOracle = Color(0xff3b2060);
  static const bubbleUser = Color(0xff482a6d);
  static const input = Color(0xff281346);
  static const bandeauOpacity = 0.24;
}

ThemeData rosaceTheme() {
  final base = ThemeData(
    brightness: Brightness.dark,
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: RosaceColors.gold,
      brightness: Brightness.dark,
      surface: RosaceColors.felt,
    ),
    scaffoldBackgroundColor: RosaceColors.felt,
    fontFamily: 'serif',
  );
  return base.copyWith(
    textTheme: GoogleFonts.sourceSans3TextTheme(base.textTheme).apply(
      bodyColor: RosaceColors.cream,
      displayColor: RosaceColors.cream,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: RosaceColors.gold,
        foregroundColor: RosaceColors.ink,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: RosaceColors.gold,
        side: const BorderSide(color: Color(0xff6f558d)),
      ),
    ),
    inputDecorationTheme: const InputDecorationTheme(
      filled: true,
      fillColor: RosaceColors.input,
    ),
  );
}

TextStyle rosaceTitleStyle({double fontSize = 40}) {
  return GoogleFonts.greatVibes(
    fontSize: fontSize,
    fontWeight: FontWeight.w400,
    color: const Color(0xfff6db9b),
    height: 0.92,
    shadows: const [
      Shadow(color: Color(0xb3120620), blurRadius: 18, offset: Offset(0, 2)),
    ],
  );
}
