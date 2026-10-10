import 'package:flutter/material.dart';

import 'tokens.g.dart';

/// Colours that the Material scheme has no slot for.
@immutable
class BrandColors extends ThemeExtension<BrandColors> {
  const BrandColors({
    required this.gold,
    required this.goldText,
    required this.ok,
    required this.warn,
    required this.info,
    required this.spa,
    required this.mute,
    required this.line,
  });

  final Color gold;
  final Color goldText;
  final Color ok;
  final Color warn;
  final Color info;
  final Color spa;
  final Color mute;
  final Color line;

  static const dark = BrandColors(
    gold: DarkTokens.gold,
    goldText: DarkTokens.gold,
    ok: DarkTokens.ok,
    warn: DarkTokens.warn,
    info: DarkTokens.info,
    spa: DarkTokens.spa,
    mute: DarkTokens.mute,
    line: DarkTokens.line,
  );

  static const light = BrandColors(
    gold: LightTokens.gold,
    goldText: LightTokens.goldText,
    ok: LightTokens.ok,
    warn: LightTokens.warn,
    info: LightTokens.info,
    spa: LightTokens.spa,
    mute: LightTokens.mute,
    line: LightTokens.line,
  );

  @override
  BrandColors copyWith() => this;

  @override
  BrandColors lerp(BrandColors? other, double t) => this;
}

extension BrandContext on BuildContext {
  BrandColors get brand => Theme.of(this).extension<BrandColors>()!;
}

const _display = 'Cormorant Garamond';
const _body = 'Manrope';

TextTheme _textTheme(Color text) {
  TextStyle body(double size, FontWeight w) =>
      TextStyle(fontFamily: _body, fontSize: size, fontWeight: w, color: text);
  TextStyle display(double size, FontWeight w) => TextStyle(
      fontFamily: _display, fontSize: size, fontWeight: w, color: text);
  return TextTheme(
    displaySmall: display(28, FontWeight.w600),
    headlineMedium: display(28, FontWeight.w600),
    headlineSmall: display(22, FontWeight.w600),
    titleLarge: display(22, FontWeight.w600),
    titleMedium: body(16, FontWeight.w700),
    titleSmall: body(14, FontWeight.w700),
    bodyLarge: body(16, FontWeight.w400),
    bodyMedium: body(14, FontWeight.w400),
    bodySmall: body(12, FontWeight.w400),
    labelLarge: body(16, FontWeight.w700),
    labelMedium: body(13, FontWeight.w600),
    labelSmall: body(11, FontWeight.w600),
  );
}

ThemeData buildTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final bg = dark ? DarkTokens.app : LightTokens.app;
  final card = dark ? DarkTokens.card : LightTokens.card;
  final text = dark ? DarkTokens.text : LightTokens.text;
  final mute = dark ? DarkTokens.mute : LightTokens.mute;
  final line = dark ? DarkTokens.line : LightTokens.line;
  final gold = dark ? DarkTokens.gold : LightTokens.goldText;
  final error = dark ? DarkTokens.error : LightTokens.error;

  final scheme = ColorScheme(
    brightness: brightness,
    primary: gold,
    onPrimary: ButtonTokens.primaryText,
    secondary: dark ? DarkTokens.wine : LightTokens.wine,
    onSecondary: Colors.white,
    error: error,
    onError: dark ? DarkTokens.ink : Colors.white,
    surface: card,
    onSurface: text,
    outline: line,
  );

  final border = OutlineInputBorder(
    borderRadius: BorderRadius.circular(SizeTokens.radiusInput),
    borderSide: BorderSide(color: line),
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: bg,
    canvasColor: bg,
    fontFamily: _body,
    textTheme: _textTheme(text),
    extensions: [dark ? BrandColors.dark : BrandColors.light],
    appBarTheme: AppBarTheme(
      backgroundColor: bg,
      foregroundColor: text,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
    cardTheme: CardThemeData(
      color: card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(SizeTokens.radiusCard),
        side: BorderSide(color: line),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: card,
      border: border,
      enabledBorder: border,
      focusedBorder: border.copyWith(
          borderSide: BorderSide(color: gold, width: 1.5)),
      errorBorder: border.copyWith(borderSide: BorderSide(color: error)),
      labelStyle: TextStyle(color: mute),
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: card,
      indicatorColor: gold.withValues(alpha: 0.18),
      height: 68,
    ),
    dividerColor: line,
  );
}
