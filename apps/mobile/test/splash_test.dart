import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/api/api.g.dart' hide AppConfig;
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/features/auth/presentation/login_screen.dart';
import 'package:priveo/features/splash/startup_progress.dart';

import 'support/fakes.dart';

/// A customer home that loads when the test says so.
class _SlowApi extends FakePriveoApi {
  final home = Completer<CustomerHome>();

  @override
  Future<CustomerHome> customerHome() => home.future;
}

double _bar(WidgetTester tester) =>
    tester.widget<FractionallySizedBox>(find.byType(FractionallySizedBox)).widthFactor!;

void main() {
  group('startup progress', () {
    const ms = Duration(milliseconds: 1);

    test('moves while the saved sign-in is read, but never past its share', () {
      double at(int t) => startupTarget(sinceStart: ms * t, sessionResolvedAt: null, loads: const []);
      expect(at(0), 0);
      expect(at(400), greaterThan(at(100)));
      expect(at(60000), lessThan(sessionShare));
    });

    test('is full at once for a signed-out phone, once the sign-in is read', () {
      expect(startupTarget(sinceStart: ms * 500, sessionResolvedAt: ms * 500, loads: const []), 1);
    });

    test('a signed-in role fills the rest only when every load has finished', () {
      double at(int t, List<bool> loads) =>
          startupTarget(sinceStart: ms * t, sessionResolvedAt: ms * 300, loads: loads);
      expect(at(300, [false]), sessionShare);
      expect(at(1500, [false]), greaterThan(sessionShare));
      expect(at(60000, [false]), lessThan(1));
      expect(at(1500, [true]), 1);
      expect(at(1500, [false]), lessThan(at(3000, [false])));
    });

    test('each finished load is worth an equal part of what is left', () {
      double at(List<bool> loads) =>
          startupTarget(sinceStart: ms * 300, sessionResolvedAt: ms * 300, loads: loads);
      // At the instant the sign-in is read nothing has crept yet.
      expect(at([true, false, false]), closeTo(sessionShare + (1 - sessionShare) / 3, 1e-9));
      expect(at([true, true, false]), closeTo(sessionShare + 2 * (1 - sessionShare) / 3, 1e-9));
      expect(at([true, true, true]), 1);
    });
  });

  group('splash screen', () {
    testWidgets('plays the scene for three seconds before it leaves', (tester) async {
      await pumpApp(tester);
      await tester.pump(const Duration(milliseconds: 2900));
      expect(find.byType(LoginScreen), findsNothing);
      expect(find.text('Care that shows.\nEvery time you drive.'), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pumpAndSettle();
      // Nobody is signed in: the splash stays, with the two welcome buttons.
      expect(find.byType(LoginScreen), findsNothing);
      expect(find.text('Get started'), findsOneWidget);
      expect(find.text('Already a member? Log in'), findsOneWidget);
      await tester.tap(find.text('Get started'));
      await tester.pumpAndSettle();
      expect(find.byType(LoginScreen), findsOneWidget);
      expect(find.text('Continue'), findsOneWidget);
      expect(find.text('Use demo account'), findsNothing);
    });

    testWidgets('both welcome buttons open the email step, and no bar is shown to a signed-out phone', (tester) async {
      await pumpApp(tester);
      await tester.pump(const Duration(milliseconds: 3100));
      await tester.pumpAndSettle();
      expect(find.byType(FractionallySizedBox), findsNothing);
      await tester.tap(find.text('Already a member? Log in'));
      await tester.pumpAndSettle();
      expect(find.text('Email, mobile or user ID'), findsOneWidget);
    });

    testWidgets('shows the bar after the scene and fills it as the first screen loads', (tester) async {
      final api = _SlowApi();
      final store = MemorySessionStore();
      await store.write(customerSession);
      await pumpApp(tester, store: store, api: api);

      // During the scene the bar is not shown, and nothing is waited for twice.
      await tester.pump(const Duration(milliseconds: 1400));
      await tester.pump(const Duration(milliseconds: 100)); // the wording follows the next frame
      expect(find.text('Loading your schedule'), findsOneWidget);
      expect(_bar(tester), 0);

      // The scene ends while the home is still loading: the bar waits, part full.
      await tester.pump(const Duration(milliseconds: 1600));
      await tester.pump(const Duration(milliseconds: 600));
      expect(_bar(tester), allOf(greaterThan(0), lessThan(1)));
      expect(find.text('Loading your schedule'), findsOneWidget);

      // The home arrives: the bar fills and the app leaves the splash.
      api.home.complete(await FakePriveoApi().customerHome());
      await tester.pumpAndSettle();
      expect(find.text('Loading your schedule'), findsNothing);
      expect(find.byType(LoginScreen), findsNothing);
    });

    testWidgets('says so when loading is slow, and gives up after twelve seconds', (tester) async {
      final api = _SlowApi();
      final store = MemorySessionStore();
      await store.write(customerSession);
      await pumpApp(tester, store: store, api: api);
      await tester.pump(const Duration(seconds: 9));
      expect(find.text('Still loading. Check your connection.'), findsOneWidget);
      await tester.pump(const Duration(seconds: 4));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('Still loading. Check your connection.'), findsNothing);
    });

    testWidgets('with reduce motion the scene is skipped and only the bar remains', (tester) async {
      tester.platformDispatcher.accessibilityFeaturesTestValue =
          const FakeAccessibilityFeatures(disableAnimations: true);
      addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
      await pumpApp(tester);
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.text('Care that shows.\nEvery time you drive.'), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 800));
      await tester.pumpAndSettle();
      expect(find.text('Get started'), findsOneWidget);
    });
  });
}
