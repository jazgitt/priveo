// Signs in to the real app as accounts from the fixture manifest and checks
// what each scenario's home and a few key screens show. It reads only; it
// never changes data. From apps/mobile, against a fixture API:
//   flutter test integration_test/scenarios_test.dart \
//     --dart-define=API_BASE_URL=<url> \
//     --dart-define=SCENARIO_MANIFEST='<compact manifest JSON>' \
//     --dart-define=SCENARIO_PASSWORD=... --dart-define=SCENARIO_ADMIN_PASSWORD=...
// See docs/testing/test-data-plan.md for the manifest and scenario list.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:priveo/features/auth/presentation/login_screen.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';
import 'package:priveo/main_dev.dart' as app;

const _manifestJson = String.fromEnvironment('SCENARIO_MANIFEST');
const _password = String.fromEnvironment('SCENARIO_PASSWORD');
const _adminPassword = String.fromEnvironment('SCENARIO_ADMIN_PASSWORD');

typedef _Check = Future<void> Function(WidgetTester tester);

/// Waits for something that depends on the network or the splash.
Future<void> _waitFor(WidgetTester tester, Finder finder) async {
  for (var i = 0; i < 150; i++) {
    await tester.pump(const Duration(milliseconds: 200));
    if (finder.evaluate().isNotEmpty) return;
  }
  fail('Timed out waiting for $finder');
}

Future<void> _tapText(WidgetTester tester, String text) async {
  final finder = find.text(text);
  await _waitFor(tester, finder);
  await tester.tap(finder.first);
  await tester.pump(const Duration(milliseconds: 300));
}

Future<void> _signIn(WidgetTester tester, String id, String password) async {
  final getStarted = find.text('Get started');
  if (getStarted.evaluate().isNotEmpty) {
    await tester.tap(getStarted);
    await tester.pumpAndSettle();
  }
  // A sign-in left on its password step shows "Change" instead of "Continue".
  await _waitFor(
    tester,
    find.byWidgetPredicate(
      (w) => w is Text && (w.data == 'Continue' || w.data == 'Change'),
    ),
  );
  if (find.text('Change').evaluate().isNotEmpty) {
    await tester.tap(find.text('Change'));
    await tester.pumpAndSettle();
  }
  await tester.enterText(find.byType(TextField), id);
  await tester.tap(find.text('Continue'));
  await _waitFor(tester, find.text('Change'));
  await tester.enterText(find.byType(TextField), password);
  await tester.tap(find.text('Sign in').last);
}

Future<void> _signOut(WidgetTester tester) async {
  await tester.tap(find.byTooltip('Sign out'));
  await _waitFor(tester, find.byType(LoginScreen));
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('manifest scenarios show the expected screens', (tester) async {
    expect(_manifestJson, isNotEmpty, reason: 'SCENARIO_MANIFEST is missing');
    expect(_password, isNotEmpty, reason: 'SCENARIO_PASSWORD is missing');
    expect(
      _adminPassword,
      isNotEmpty,
      reason: 'SCENARIO_ADMIN_PASSWORD is missing',
    );
    final manifest = jsonDecode(_manifestJson) as Map<String, dynamic>;
    final scenarios = {
      for (final s in manifest['scenarios'] as List)
        (s as Map<String, dynamic>)['id'] as String: s,
    };
    String customer(String id) => scenarios[id]!['customer_login'] as String;
    String crew(String id, int index) =>
        (scenarios[id]!['crew_logins'] as List)[index] as String;

    app.main();
    final login = find.byType(LoginScreen);
    await _waitFor(
      tester,
      find.byWidgetPredicate(
        (w) => w is LoginScreen || (w is IconButton && w.tooltip == 'Sign out'),
      ),
    );
    if (find.byTooltip('Sign out').evaluate().isNotEmpty) {
      await _signOut(tester);
    }

    // Home labels that only one role's home shows.
    Future<void> customerHome(WidgetTester t) async {
      // Home greets by the hour, so wait for the greeting line itself.
      await _waitFor(t, find.byType(GreetingLine));
    }

    final steps = <(String, String, String, _Check)>[
      // (label, login id, password, what to check once signed in)
      ('C01 customer home', customer('C01'), _password, customerHome),
      (
        'C09 multi-vehicle customer home',
        customer('C09'),
        _password,
        customerHome,
      ),
      (
        'C12 customer sees its complaints',
        customer('C12'),
        _password,
        (t) async {
          await customerHome(t);
          await _tapText(t, 'Support');
          await _tapText(t, 'My complaints');
          await _waitFor(t, find.text('My complaints'));
          await t.pump(const Duration(seconds: 2));
          expect(
            find.text('You have not raised any complaints.'),
            findsNothing,
          );
        },
      ),
      (
        'C18 onboarding incomplete',
        customer('C18'),
        _password,
        (t) async {
          await _waitFor(
            t,
            find.text(
              'Check what we have, and fill in anything that is missing.',
            ),
          );
        },
      ),
      (
        'R01 crew home',
        crew('R01', 0),
        _password,
        (t) async {
          await _waitFor(t, find.text('Total'));
        },
      ),
      (
        'A01 admin home',
        'priveopapa',
        _adminPassword,
        (t) async {
          await _waitFor(t, find.text('Payments to confirm'));
        },
      ),
    ];

    final failures = <String>[];
    for (final (label, id, password, check) in steps) {
      try {
        await _signIn(tester, id, password);
        await check(tester);
      } catch (e) {
        failures.add('$label: $e');
      }
      // Recover to the sign-in screen whatever happened.
      try {
        // A check may leave a pushed screen open; go back to the shell first.
        for (
          var i = 0;
          i < 4 &&
              find.byTooltip('Sign out').evaluate().isEmpty &&
              login.evaluate().isEmpty;
          i++
        ) {
          await tester.pageBack();
          await tester.pump(const Duration(milliseconds: 500));
        }
        if (find.byTooltip('Sign out').evaluate().isNotEmpty) {
          await _signOut(tester);
        } else if (login.evaluate().isEmpty) {
          await _waitFor(tester, login);
        }
      } catch (e) {
        failures.add('$label: could not return to sign-in: $e');
        break;
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });
}
