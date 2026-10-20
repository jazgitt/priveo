// Real screens, real API client, real fixture data. Signs in as accounts from
// the fixture manifest and checks what each scenario shows. No emulator.
//
// Skipped unless SCENARIO_API_URL is set. Easiest way to run it, from the
// repository root:  tools/test-data/run-widget-scenarios.ps1
// By hand, with a fixture API running:
//   flutter test test/scenarios --dart-define=SCENARIO_API_URL=http://127.0.0.1:8011 \
//     --dart-define=SCENARIO_MANIFEST_FILE=<path to manifest.json> \
//     --dart-define=SCENARIO_PASSWORD=... --dart-define=SCENARIO_ADMIN_PASSWORD=...
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario screens', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }

  final scenarios = loadScenarios();
  String customer(String id) => scenarios[id]!['customer_login'] as String;
  String crew(String id, [int index = 0]) =>
      (scenarios[id]!['crew_logins'] as List)[index] as String;

  setUpAll(() {
    // flutter_test blocks real sockets; this suite talks to a local API.
    HttpOverrides.global = null;
  });

  group('customer home', () {
    // Every other customer scenario with a vehicle opens Home with its
    // greeting; the ones below also show what makes the scenario different.
    final expected = <String, ({List<String> shows, List<String> hides})>{
      'C01': (
        shows: ['No subscription', 'No plan', 'Deep Spa'],
        hides: ['Skip or Pause', 'My subscription', 'NEXT SERVICE'],
      ),
      'C09': (
        shows: ['TS 09 TT 0001', 'TS 09 TT 0002', 'Active', 'Skip or Pause'],
        hides: ['No subscription'],
      ),
      'C19': (shows: ['Activating', 'Not scheduled yet'], hides: ['Deep Spa']),
      'C20': (
        shows: ['Inactive', 'Not scheduled yet'],
        hides: ['Deep Spa', 'Activating'],
      ),
      'C21': (shows: ['Active', 'Deep Spa', 'Scheduled'], hides: ['Inactive']),
      'C23': (shows: ['Monthly check-in', 'Active'], hides: ['Inactive']),
    };
    final plain = [
      'C02',
      'C03',
      'C04',
      'C05',
      'C06',
      'C07',
      'C08',
      'C10',
      'C11',
      'C12',
      'C13',
      'C14',
      'C15',
      'C16',
      'C17',
      'C22',
      'C24',
      'C25',
      'C26',
      'C27',
      'C29',
    ];
    for (final id in [...expected.keys, ...plain]) {
      testWidgets('$id opens Home [HOME-02]', (tester) async {
        await openApp(
          tester,
          await signInApi(tester, customer(id), scenarioPassword),
        );
        await untilFound(tester, find.byType(GreetingLine));
        final want = expected[id];
        if (want == null) return;
        // Let the next-service card and quick actions load.
        await until(tester, () => false, timeout: const Duration(seconds: 3));
        for (final text in want.shows) {
          expect(
            find.text(text),
            findsWidgets,
            reason: '$id should show "$text"',
          );
        }
        for (final text in want.hides) {
          expect(
            find.text(text),
            findsNothing,
            reason: '$id should not show "$text"',
          );
        }
      });
    }

    testWidgets('C18 resumes onboarding at step 1 of 7 [ONB-25]', (tester) async {
      await openApp(
        tester,
        await signInApi(tester, customer('C18'), scenarioPassword),
      );
      await untilFound(tester, find.text('Step 1 of 7'));
      expect(
        find.text('Check what we have, and fill in anything that is missing.'),
        findsOneWidget,
      );
      expect(find.byType(GreetingLine), findsNothing);
    });

    testWidgets('C28 has an account but no vehicle', (tester) async {
      await openApp(
        tester,
        await signInApi(tester, customer('C28'), scenarioPassword),
      );
      await untilFound(
        tester,
        find.text('No vehicle is on your account yet. Contact Priveo.'),
      );
    });
  });

  group('sign-in rules', () {
    testWidgets('a wrong password gets the API message [AUTH-13]', (tester) async {
      Object? error;
      try {
        await signInApi(tester, customer('C01'), 'definitely-wrong');
      } catch (e) {
        error = e;
      }
      expect(error, isA<ApiFailure>());
      expect(
        (error as ApiFailure).message,
        'The ID or password is not correct.',
      );
    });
  });

  group('crew home', () {
    for (final id in ['R01', 'R02', 'R03', 'R05', 'R06']) {
      testWidgets('$id crew sees the day counts [CRW-SCH-01]', (tester) async {
        await openApp(
          tester,
          await signInApi(tester, crew(id), scenarioPassword),
        );
        await untilFound(tester, find.text('Total'));
      });
    }
  });

  group('admin home', () {
    testWidgets('admin sees payments to confirm [ADM-ACC-07]', (tester) async {
      await openApp(
        tester,
        await signInApi(tester, 'priveopapa', scenarioAdminPassword),
      );
      await untilFound(tester, find.text('Payments to confirm'));
    });
  });

  group('scenario details', () {
    testWidgets('C12 lists its complaints [CMP-01]', (tester) async {
      await openApp(
        tester,
        await signInApi(tester, customer('C12'), scenarioPassword),
      );
      await untilFound(tester, find.byType(GreetingLine));
      await tapFinder(tester, find.text('Support'));
      await tapFinder(tester, find.text('My complaints'));
      await until(
        tester,
        () => find
            .text('You have not raised any complaints.')
            .evaluate()
            .isNotEmpty,
        timeout: const Duration(seconds: 6),
      );
      expect(find.text('You have not raised any complaints.'), findsNothing);
    });
  });
}
