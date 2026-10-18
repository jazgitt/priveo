import 'dart:convert';
import 'dart:io';

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/auth/data/support_contact.dart';
import 'package:priveo/features/auth/presentation/auth_strings.dart';
import 'package:priveo/features/auth/presentation/login_screen.dart';
import 'package:priveo/features/support/widgets.dart' show linkOpenerProvider;
import 'package:priveo/l10n/app_localizations.dart';

import '../support/fakes.dart';

Future<List<Uri>> pumpLogin(WidgetTester tester) async {
  final opened = <Uri>[];
  tester.view.physicalSize = const Size(800, 2000);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(ProviderScope(
    overrides: [
      authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
      authSupportContactProvider.overrideWith((ref) async =>
          const AuthSupportContact(
              helpline: '+911234567890', whatsapp: '+91 98765 43210')),
      authLegalLinksProvider.overrideWith((ref) async => {'terms': termsUri.toString(), 'privacy': privacyUri.toString()}),
      linkOpenerProvider.overrideWithValue((uri) async {
        opened.add(uri);
        return true;
      }),
    ],
    child: MaterialApp(
      theme: customerTheme,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: const LoginScreen(),
    ),
  ));
  await tester.pumpAndSettle();
  return opened;
}

void main() {
  testWidgets('the sign-in screen opens on the email step, with no welcome step or demo accounts',
      (tester) async {
    await pumpLogin(tester);
    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('Email, mobile or user ID'), findsOneWidget);
    expect(find.text('Continue'), findsOneWidget);
    expect(find.text('Get started'), findsNothing);
    expect(find.text('Already a member? Log in'), findsNothing);
    expect(find.text('Use demo account'), findsNothing);
    expect(find.text('Customer'), findsNothing);
    expect(find.text('Crew'), findsNothing);
    expect(find.text('Admin'), findsNothing);
  });

  testWidgets('an email with a bad format shows an error', (tester) async {
    await pumpLogin(tester);
    await tester.enterText(find.byType(TextField), 'asha@example');
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    expect(find.text('Enter a valid email address.'), findsOneWidget);
  });

  testWidgets('not registered shows the support buttons', (tester) async {
    final opened = await pumpLogin(tester);
    await tester.enterText(find.byType(TextField), 'stranger@priveo.test');
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    expect(find.text(FakeAuthRepository.notRegistered), findsOneWidget);

    await tester.tap(find.text('Call support'));
    await tester.tap(find.text('WhatsApp support'));
    expect(opened.map((u) => u.toString()),
        ['tel:+911234567890', 'https://wa.me/919876543210']);
  });

  testWidgets('the Terms and Privacy Policy words open links', (tester) async {
    final opened = await pumpLogin(tester);
    final rich = tester.widget<RichText>(find
        .byWidgetPredicate((w) =>
            w is RichText && w.text.toPlainText().contains('Privacy Policy'))
        .first);
    final spans = <TextSpan>[];
    rich.text.visitChildren((s) {
      if (s is TextSpan && s.recognizer is TapGestureRecognizer) spans.add(s);
      return true;
    });
    for (final s in spans) {
      (s.recognizer! as TapGestureRecognizer).onTap!();
    }
    await tester.pumpAndSettle();
    expect(opened, [termsUri, privacyUri]);
  });

  test('the ARB fragment has the same keys and words as the code', () {
    final arb = jsonDecode(File('lib/l10n/fragments/auth.arb').readAsStringSync())
        as Map<String, dynamic>;
    expect(arb, AuthText.all);
  });
}
