// Real screens, real API client, real fixture data. Signs in as accounts from
// the fixture manifest and checks what each scenario shows. No emulator.
//
// Skipped unless SCENARIO_API_URL is set. Easiest way to run it, from the
// repository root:  tools/test-data/run-widget-scenarios.ps1
// By hand, with a fixture API running:
//   flutter test test/scenarios --dart-define=SCENARIO_API_URL=http://127.0.0.1:8011 \
//     --dart-define=SCENARIO_MANIFEST_FILE=<path to manifest.json> \
//     --dart-define=SCENARIO_PASSWORD=... --dart-define=SCENARIO_ADMIN_PASSWORD=...
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/app.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/config/app_config.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/features/crew/crew_providers.dart';
import 'package:priveo/features/crew/upload/upload_queue.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';

const _url = String.fromEnvironment('SCENARIO_API_URL');
const _manifestFile = String.fromEnvironment('SCENARIO_MANIFEST_FILE');
const _password = String.fromEnvironment('SCENARIO_PASSWORD');
const _adminPassword = String.fromEnvironment('SCENARIO_ADMIN_PASSWORD');

/// Real time passes while the real client waits for the real server.
Future<void> _until(
  WidgetTester tester,
  bool Function() done, {
  Duration timeout = const Duration(seconds: 25),
}) async {
  final end = DateTime.now().add(timeout);
  await tester.runAsync(() async {
    while (!done() && DateTime.now().isBefore(end)) {
      await Future<void>.delayed(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));
    }
  });
}

Future<void> _untilFound(WidgetTester tester, Finder finder) async {
  await _until(tester, () => finder.evaluate().isNotEmpty);
  expect(finder, findsWidgets);
}

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await _untilFound(tester, finder);
  await tester.tap(finder.first);
  await tester.pump(const Duration(milliseconds: 300));
}

Future<Session> _login(WidgetTester tester, String id, String password) async {
  Session? session;
  Object? failure;
  await tester.runAsync(() async {
    final container = ProviderContainer(
      overrides: [
        appConfigProvider.overrideWithValue(
          const AppConfig(
            flavor: Flavor.dev,
            apiBaseUrl: _url,
            showDemoAccounts: false,
          ),
        ),
      ],
    );
    try {
      session = await container
          .read(authRepositoryProvider)
          .login(id, password);
    } catch (e) {
      // runAsync would swallow it; rethrow outside.
      failure = e;
    } finally {
      container.dispose();
    }
  });
  if (failure != null) throw failure!;
  return session!;
}

/// The real app, signed in, with the real client. Only the plugins a test
/// cannot have (push, connectivity, SQLite) are replaced.
Future<void> _openApp(WidgetTester tester, Session session) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.5;
  addTearDown(tester.view.reset);
  final store = MemorySessionStore();
  await store.write(session);
  final container = ProviderContainer(
    overrides: [
      readRefreshProvider.overrideWith((ref) => const Stream<int>.empty()),
      appConfigProvider.overrideWithValue(
        const AppConfig(
          flavor: Flavor.dev,
          apiBaseUrl: _url,
          showDemoAccounts: false,
        ),
      ),
      sessionStoreProvider.overrideWithValue(store),
      uploadQueueStoreProvider.overrideWithValue(MemoryUploadQueueStore()),
      onlineEventsProvider.overrideWithValue(null),
    ],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const PriveoApp()),
  );
}

void main() {
  if (_url.isEmpty) {
    test('scenario screens', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }

  final manifest =
      jsonDecode(File(_manifestFile).readAsStringSync())
          as Map<String, dynamic>;
  final scenarios = {
    for (final s in manifest['scenarios'] as List)
      (s as Map<String, dynamic>)['id'] as String: s,
  };
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
      testWidgets('$id opens Home', (tester) async {
        await _openApp(tester, await _login(tester, customer(id), _password));
        await _untilFound(tester, find.byType(GreetingLine));
        final want = expected[id];
        if (want == null) return;
        // Let the next-service card and quick actions load.
        await _until(tester, () => false, timeout: const Duration(seconds: 3));
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

    testWidgets('C18 resumes onboarding at step 1 of 7', (tester) async {
      await _openApp(tester, await _login(tester, customer('C18'), _password));
      await _untilFound(tester, find.text('Step 1 of 7'));
      expect(
        find.text('Check what we have, and fill in anything that is missing.'),
        findsOneWidget,
      );
      expect(find.byType(GreetingLine), findsNothing);
    });

    testWidgets('C28 has an account but no vehicle', (tester) async {
      await _openApp(tester, await _login(tester, customer('C28'), _password));
      await _untilFound(
        tester,
        find.text('No vehicle is on your account yet. Contact Priveo.'),
      );
    });
  });

  group('sign-in rules', () {
    testWidgets('a wrong password gets the API message', (tester) async {
      Object? error;
      try {
        await _login(tester, customer('C01'), 'definitely-wrong');
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
      testWidgets('$id crew sees the day counts', (tester) async {
        await _openApp(tester, await _login(tester, crew(id), _password));
        await _untilFound(tester, find.text('Total'));
      });
    }
  });

  group('admin home', () {
    testWidgets('admin sees payments to confirm', (tester) async {
      await _openApp(
        tester,
        await _login(tester, 'priveopapa', _adminPassword),
      );
      await _untilFound(tester, find.text('Payments to confirm'));
    });
  });

  group('scenario details', () {
    testWidgets('C12 lists its complaints', (tester) async {
      await _openApp(tester, await _login(tester, customer('C12'), _password));
      await _untilFound(tester, find.byType(GreetingLine));
      await _tap(tester, find.text('Support'));
      await _tap(tester, find.text('My complaints'));
      await _until(
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
