import 'package:flutter/material.dart';

import 'tokens.g.dart';

/// Each role has its own look. The splash and login use the customer look.
enum AppLook {
  /// Dark, matched to the prototype.
  customer,

  /// Plain white. DERIVED: the owner asked for a white crew theme; the white
  /// background below is not in tokens.json.
  crew,

  /// Cream, the light palette in tokens.json.
  admin,
}

/// Colours that the Material scheme has no slot for.
@immutable
class BrandColors extends ThemeExtension<BrandColors> {
  const BrandColors({
    required this.gold,
    required this.goldText,
    required this.goldHi,
    required this.ok,
    required this.warn,
    required this.info,
    required this.spa,
    required this.mute,
    required this.dim,
    required this.line,
    required this.hair,
    required this.card2,
  });

  final Color gold;
  final Color goldText;

  /// Bright gold for small text on a dark background.
  final Color goldHi;
  final Color ok;
  final Color warn;
  final Color info;
  final Color spa;
  final Color mute;

  /// Dimmer than [mute]: placeholders and unselected tabs.
  final Color dim;
  final Color line;

  /// The faint gold border around cards.
  final Color hair;

  /// The fill of inputs.
  final Color card2;

  static const dark = BrandColors(
    gold: DarkTokens.gold,
    goldText: DarkTokens.gold,
    goldHi: DarkTokens.goldHi,
    ok: DarkTokens.ok,
    warn: DarkTokens.warn,
    info: DarkTokens.info,
    spa: DarkTokens.spa,
    mute: DarkTokens.mute,
    dim: DarkTokens.dim,
    line: DarkTokens.line,
    hair: DarkTokens.hair,
    card2: DarkTokens.card2,
  );

  static const light = BrandColors(
    gold: LightTokens.gold,
    goldText: LightTokens.goldText,
    goldHi: LightTokens.goldText,
    ok: LightTokens.ok,
    warn: LightTokens.warn,
    info: LightTokens.info,
    spa: LightTokens.spa,
    mute: LightTokens.mute,
    dim: LightTokens.mute,
    line: LightTokens.line,
    hair: LightTokens.line,
    card2: LightTokens.card,
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

/// Sizes taken from the prototype for the customer look. tokens.json says
/// 18 for cards and 12 for inputs; the other looks keep those.
const _prototypeCardRadius = 22.0;
const _prototypeInputRadius = 15.0;

TextTheme _textTheme(Color text, {required bool prototype}) {
  TextStyle body(double size, FontWeight w) =>
      TextStyle(fontFamily: _body, fontSize: size, fontWeight: w, color: text);
  TextStyle display(double size, FontWeight w) => TextStyle(
    fontFamily: _display,
    fontSize: size,
    fontWeight: w,
    color: text,
    height: 1.05,
  );
  return TextTheme(
    displaySmall: display(prototype ? 34 : 28, FontWeight.w600),
    headlineMedium: display(prototype ? 32 : 28, FontWeight.w600),
    headlineSmall: display(prototype ? 26 : 22, FontWeight.w600),
    titleLarge: display(prototype ? 24 : 22, FontWeight.w600),
    titleMedium: body(16, FontWeight.w700),
    titleSmall: body(14, FontWeight.w700),
    bodyLarge: body(16, FontWeight.w400),
    bodyMedium: body(14, FontWeight.w400),
    bodySmall: body(12, FontWeight.w400),
    labelLarge: body(16, FontWeight.w700),
    labelMedium: body(13, FontWeight.w600),
    labelSmall: body(11, FontWeight.w700),
  );
}

ThemeData buildTheme(AppLook look) {
  final dark = look == AppLook.customer;
  final brightness = dark ? Brightness.dark : Brightness.light;
  final bg = switch (look) {
    AppLook.customer => DarkTokens.app,
    AppLook.crew => const Color(0xFFFFFFFF),
    AppLook.admin => LightTokens.app,
  };
  final card = dark ? DarkTokens.card : LightTokens.card;
  final text = dark ? DarkTokens.text : LightTokens.text;
  final mute = dark ? DarkTokens.mute : LightTokens.mute;
  final line = dark ? DarkTokens.line : LightTokens.line;
  final gold = dark ? DarkTokens.gold : LightTokens.goldText;
  final error = dark ? DarkTokens.error : LightTokens.error;
  final brand = dark ? BrandColors.dark : BrandColors.light;
  final cardRadius = dark ? _prototypeCardRadius : SizeTokens.radiusCard;
  final inputRadius = dark ? _prototypeInputRadius : SizeTokens.radiusInput;

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
    borderRadius: BorderRadius.circular(inputRadius),
    borderSide: BorderSide(color: line),
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: bg,
    canvasColor: bg,
    fontFamily: _body,
    textTheme: _textTheme(text, prototype: dark),
    extensions: [brand],
    iconTheme: IconThemeData(color: text, size: 22, weight: 300),
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
        borderRadius: BorderRadius.circular(cardRadius),
        side: BorderSide(color: brand.hair),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: brand.card2,
      border: border,
      enabledBorder: border,
      disabledBorder: border,
      focusedBorder: border.copyWith(borderSide: BorderSide(color: gold)),
      errorBorder: border.copyWith(borderSide: BorderSide(color: error)),
      labelStyle: TextStyle(color: mute),
      hintStyle: TextStyle(color: brand.dim, fontWeight: FontWeight.w500),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: text,
        minimumSize: const Size(0, SizeTokens.touchTargetMin),
        side: BorderSide(color: line),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(SizeTokens.radiusButton),
        ),
        textStyle: const TextStyle(
          fontFamily: _body,
          fontSize: 15,
          fontWeight: FontWeight.w700,
        ),
      ),
    ),
    dividerColor: line,
  );
}

final customerTheme = buildTheme(AppLook.customer);
final crewTheme = buildTheme(AppLook.crew);
final adminTheme = buildTheme(AppLook.admin);
