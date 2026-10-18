// Signing in through the real screens against the real fixture API (AUTH):
// the welcome screen, an unregistered email, password sign-in for each role,
// a wrong password, and the first sign-in with the emailed code (C30 has no
// password yet; the fixture API's fixed dev code is 246810). Needs the
// fixture API; see scenario_screens_test.dart.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/ui/widgets.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';

import 'scenario_support.dart';

const _devCode = '246810';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario sign-in', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }
  setUpAll(() => HttpOverrides.global = null);
  final scenarios = loadScenarios();
  String customer(String id) => scenarios[id]!['customer_login'] as String;
  String crew(String id, int i) =>
      (scenarios[id]!['crew_logins'] as List)[i] as String;

  /// Starts on the splash, which has the welcome buttons, and opens the email step.
  Future<void> openSignIn(WidgetTester tester) async {
    await openApp(tester);
    await untilFound(tester, find.text('Get started'));
    await tapFinder(tester, find.text('Get started'));
    await untilFound(tester, find.text('Continue'));
  }

  Future<void> enterIdAndPassword(
    WidgetTester tester,
    String id,
    String password,
  ) async {
    await tester.enterText(find.byType(TextField), id);
    await tapFinder(tester, find.text('Continue'));
    await untilFound(tester, find.text('Change'));
    await tester.enterText(find.byType(TextField), password);
    // "Sign in" is also the heading; the button is the one to tap.
    await tapFinder(tester, find.widgetWithText(PrimaryButton, 'Sign in'));
  }

  group('welcome and email step', () {
    testWidgets('the welcome screen offers Get started and Log in', (
      tester,
    ) async {
      await openApp(tester);
      await untilFound(tester, find.text('Get started'));
      expect(find.text('Care that shows.\nEvery time you drive.'), findsOneWidget);
      expect(find.text('Get started'), findsOneWidget);
      expect(find.text('Already a member? Log in'), findsOneWidget);

      await tapFinder(tester, find.text('Already a member? Log in'));
      await untilFound(tester, find.text('Email, mobile or user ID'));
      expect(find.text('Continue'), findsOneWidget);
      expect(
        find.text('By continuing you accept the Terms and the Privacy Policy.'),
        findsOneWidget,
      );
      await letTimersFinish(tester);
    });

    testWidgets('an email Priveo does not know is told to contact Priveo', (
      tester,
    ) async {
      await openSignIn(tester);
      await tester.enterText(find.byType(TextField), 'nobody@priveo.test');
      await tapFinder(tester, find.text('Continue'));
      await untilFound(
        tester,
        find.text('This email is not registered. Contact Priveo.'),
      );
      await untilFound(tester, find.text('Call support'));
      expect(find.text('WhatsApp support'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });

  group('password sign-in', () {
    testWidgets('a customer signs in by email and password', (tester) async {
      await openSignIn(tester);
      await enterIdAndPassword(tester, customer('C01'), scenarioPassword);
      await untilFound(tester, find.byType(GreetingLine));
      await letTimersFinish(tester);
    });

    testWidgets('a wrong password does not sign in and offers a reset', (
      tester,
    ) async {
      await openSignIn(tester);
      await enterIdAndPassword(tester, customer('C01'), 'wrong-password-1');
      await untilFound(tester, find.text('The ID or password is not correct.'));
      expect(find.text('Forgot password?'), findsOneWidget);
      expect(find.byType(GreetingLine), findsNothing);
      await letTimersFinish(tester);
    });

    testWidgets('crew sign in by mobile number', (tester) async {
      await openSignIn(tester);
      await enterIdAndPassword(tester, crew('R01', 1), scenarioPassword);
      await untilFound(tester, find.text('TS30TT0001'));
      expect(find.text('Total'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('the admin signs in by user ID', (tester) async {
      await openSignIn(tester);
      await enterIdAndPassword(tester, 'priveopapa', scenarioAdminPassword);
      await untilFound(tester, find.text('Payments to confirm'));
      await letTimersFinish(tester);
    });
  });

  group('crew accounts that cannot sign in (R04)', () {
    testWidgets('an inactive crew account is refused', (tester) async {
      Object? error;
      try {
        await signInApi(tester, crew('R04', 4), scenarioPassword);
      } catch (e) {
        error = e;
      }
      expect(error, isA<ApiFailure>());
      expect((error as ApiFailure).statusCode, 401);
      expect(error.message, 'The ID or password is not correct.');
    });

    testWidgets('a locked crew account says to ask the admin', (tester) async {
      Object? error;
      try {
        await signInApi(tester, crew('R04', 5), scenarioPassword);
      } catch (e) {
        error = e;
      }
      expect(error, isA<ApiFailure>());
      expect((error as ApiFailure).statusCode, 403);
      expect(
        error.message,
        'This login is locked. Ask the admin to reset your password.',
      );
    });
  });

  group('first sign-in (C30)', () {
    testWidgets('the emailed code, a new password, then onboarding', (
      tester,
    ) async {
      await openSignIn(tester);
      await tester.enterText(find.byType(TextField), customer('C30'));
      await tapFinder(tester, find.text('Continue'));

      // No password yet, so a code is emailed.
      await untilFound(tester, find.text('Enter the code'));
      expect(find.textContaining('We sent a 6-digit code to'), findsOneWidget);
      expect(find.textContaining(customer('C30')), findsWidgets);
      expect(find.text('Change email'), findsOneWidget);

      await tester.enterText(find.byType(TextField), '000000');
      await tapFinder(tester, find.text('Verify'));
      await untilFound(tester, find.text('The code is not correct.'));

      await tester.enterText(find.byType(TextField), _devCode);
      await tapFinder(tester, find.text('Verify'));
      await untilFound(tester, find.text('Set a password'));

      const rule = 'Use at least 8 characters, with a letter and a number.';
      expect(find.text(rule), findsOneWidget);
      await tester.enterText(find.byType(TextField).at(0), 'abc');
      await tester.enterText(find.byType(TextField).at(1), 'abc');
      await tapFinder(tester, find.text('Save and continue'));
      expect(find.text(rule), findsNWidgets(2));

      await tester.enterText(find.byType(TextField).at(0), 'NewPassword123');
      await tester.enterText(find.byType(TextField).at(1), 'Different123');
      await tapFinder(tester, find.text('Save and continue'));
      expect(find.text('The two passwords do not match.'), findsOneWidget);

      await tester.enterText(find.byType(TextField).at(1), 'NewPassword123');
      await tapFinder(tester, find.text('Save and continue'));

      // Signed in, and onboarding starts with the customer's details.
      await untilFound(tester, find.text('Step 1 of 7'));
      expect(find.text('Your details'), findsOneWidget);
      expect(find.byType(GreetingLine), findsNothing);
      await letTimersFinish(tester);
    });
  });
}
