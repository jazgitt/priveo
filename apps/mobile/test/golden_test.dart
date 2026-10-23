// Golden images of the splash end state, the login screen and the three
// homes. Each has one look: the customer side is dark, crew is white and
// admin is cream.
//
// The images are made and compared on Linux only (the CI machine), because
// text renders a little differently on each system. To remake them, add the
// label "update-goldens" to the pull request: the mobile-goldens workflow
// commits the new images to the branch.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/features/crew/home/crew_home_data.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';

import 'support/fakes.dart';

/// Loads the fonts the app ships, so the images show real text and icons.
Future<void> _loadAppFonts() async {
  final manifest = jsonDecode(await rootBundle.loadString('FontManifest.json'))
      as List<dynamic>;
  for (final family in manifest.cast<Map<String, dynamic>>()) {
    final loader = FontLoader(family['family'] as String);
    for (final font in (family['fonts'] as List).cast<Map<String, dynamic>>()) {
      loader.addFont(rootBundle.load(font['asset'] as String));
    }
    await loader.load();
  }
}

/// Decodes the images on screen. Without this they are blank in a test.
Future<void> _loadImages(WidgetTester tester) async {
  final images = find.byType(Image).evaluate().toList();
  await tester.runAsync(() async {
    for (final e in images) {
      await precacheImage((e.widget as Image).image, e);
    }
  });
}

/// The images show a greeting that depends on the hour and a date line. Pin
/// both, so they do not change with the time the test runs.
final _pinnedNow = DateTime(2026, 10, 23, 9, 30);

class _PinnedCrewDay extends CrewDayNotifier {
  @override
  DateTime? build() =>
      DateTime(_pinnedNow.year, _pinnedNow.month, _pinnedNow.day);
}

Future<void> _open(WidgetTester tester,
    {Session? session, FakePriveoApi? api}) async {
  tester.view.physicalSize = const Size(780, 1688);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final store = MemorySessionStore();
  if (session != null) await store.write(session);
  // Each role has one look, whatever the phone setting is.
  await pumpApp(tester, store: store, api: api, overrides: [
    homeNowProvider.overrideWithValue(() => _pinnedNow),
    crewDayProvider.overrideWith(_PinnedCrewDay.new),
  ]);
}

void main() {
  setUpAll(() async {
    await _loadAppFonts();
    // The debug banner is not part of the design.
    WidgetsApp.debugAllowBannerOverride = false;
  });
  tearDownAll(() => WidgetsApp.debugAllowBannerOverride = true);

  final bool skip = !Platform.isLinux;

  testWidgets('splash end state', (tester) async {
    await _open(tester);
    await _loadImages(tester);
    // The scene takes 3 seconds; this is its end state, before the progress bar.
    await tester.pump(const Duration(milliseconds: 2950));
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/splash.png'));
    await passSplash(tester);
  }, skip: skip);

  testWidgets('login', (tester) async {
    await _open(tester);
    await passSplash(tester);
    await _loadImages(tester);
    await tester.pumpAndSettle();
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/login.png'));
  }, skip: skip);

  // The review at first sign-in: the details step, and a vehicle step.
  testWidgets('onboarding review', (tester) async {
    await _open(tester,
        session: customerSession,
        api: FakePriveoApi(onboardingConfirmed: false));
    await passSplash(tester);
    await _loadImages(tester);
    await tester.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('goldens/onboarding_details.png'));

    await tester.enterText(find.byType(TextField).at(1), 'Mehta');
    for (var i = 0; i < 2; i++) {
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
    }
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('goldens/onboarding_vehicle.png'));
  }, skip: skip);

  // Customer is dark, crew is white, admin is cream.
  for (final session in [customerSession, crewSession, adminSession]) {
    final role = session.role.name;
    testWidgets('$role home', (tester) async {
      await _open(tester, session: session);
      await passSplash(tester);
      await _loadImages(tester);
      await tester.pumpAndSettle();
      await expectLater(find.byType(MaterialApp),
          matchesGoldenFile('goldens/${role}_home.png'));
    }, skip: skip);
  }
}
