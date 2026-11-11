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

  /// Starts on the splash, which has the welcome buttons, and opens the mobile number step.
  Future<void> openSignIn(WidgetTester tester) async {
    await openApp(tester);
    await untilFound(tester, find.text('Get started'));
    await tapFinder(tester, find.text('Get started'));
    await untilFound(tester, find.text('Continue'));
  }

  Future<void> enterIdAndPassword(
    WidgetTester tester,
    String id,
    String password, {
    bool crew = false,
  }) async {
    await tester.enterText(find.byType(TextField), id);
    await tester.pumpAndSettle();
    if (crew) await tapFinder(tester, find.text('Crew'));
    await tapFinder(tester, find.text('Continue'));
    await untilFound(tester, find.text('Change'));
    await tester.enterText(find.byType(TextField), password);
    // "Sign in" is also the heading; the button is the one to tap.
    await tapFinder(tester, find.widgetWithText(PrimaryButton, 'Sign in'));
  }

  group('welcome and mobile number step', () {
    testWidgets('the welcome screen offers Get started and Log in [AUTH-01]', (
      tester,
    ) async {
      await openApp(tester);
      await untilFound(tester, find.text('Get started'));
      expect(find.text('Care that shows.\nEvery time you drive.'), findsOneWidget);
      expect(find.text('Get started'), findsOneWidget);
      expect(find.text('Already a member? Log in'), findsOneWidget);

      await tapFinder(tester, find.text('Already a member? Log in'));
      await untilFound(tester, find.text('Mobile number or user ID'));
      expect(find.text('Continue'), findsOneWidget);
      expect(
        find.text('By continuing you accept the Terms and the Privacy Policy.'),
        findsOneWidget,
      );
      await letTimersFinish(tester);
    });

    testWidgets(
      'a mobile number Priveo does not know is told to contact Priveo [AUTH-15]',
      (tester) async {
        await openSignIn(tester);
        await tester.enterText(find.byType(TextField), '9111111111');
        await tapFinder(tester, find.text('Continue'));
        await untilFound(tester, find.text('Forgot MPIN?'));
        await tapFinder(tester, find.text('Forgot MPIN?'));
        await untilFound(
          tester,
          find.text('This mobile number is not registered. Contact Priveo.'),
        );
        await untilFound(tester, find.text('Call support'));
        expect(find.text('WhatsApp support'), findsOneWidget);
        await letTimersFinish(tester);
      },
    );
  });

  group('MPIN and password sign-in', () {
    testWidgets('a customer signs in by mobile number and MPIN [AUTH-13]', (
      tester,
    ) async {
      await openSignIn(tester);
      await enterIdAndPassword(tester, customer('C01'), scenarioPassword);
      await untilFound(tester, find.byType(GreetingLine));
      await letTimersFinish(tester);
    });

    testWidgets(
      'a wrong MPIN does not sign in and offers a reset [AUTH-13, AUTH-16]',
      (tester) async {
        await openSignIn(tester);
        await enterIdAndPassword(tester, customer('C01'), '000000');
        await untilFound(
          tester,
          find.text('The mobile number or MPIN is not correct.'),
        );
        expect(find.text('Forgot MPIN?'), findsOneWidget);
        expect(find.byType(GreetingLine), findsNothing);
        await letTimersFinish(tester);
      },
    );

    testWidgets('crew sign in by mobile number [CRW-ACC-02, CRW-ACC-03]', (
      tester,
    ) async {
      await openSignIn(tester);
      await enterIdAndPassword(
        tester,
        crew('R01', 1),
        scenarioPassword,
        crew: true,
      );
      await untilFound(tester, find.text('TS30TT0001'));
      expect(find.text('Total'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('the admin signs in by user ID [ADM-ACC-06]', (tester) async {
      await openSignIn(tester);
      await enterIdAndPassword(tester, 'test-admin-id', scenarioAdminPassword);
      await untilFound(tester, find.text('Payments to confirm'));
      await letTimersFinish(tester);
    });
  });

  group('crew accounts that cannot sign in (R04)', () {
    testWidgets('an inactive crew account is refused [CRW-ACC-08]', (tester) async {
      Object? error;
      try {
        await signInApi(tester, crew('R04', 4), scenarioPassword, role: 'crew');
      } catch (e) {
        error = e;
      }
      expect(error, isA<ApiFailure>());
      expect((error as ApiFailure).statusCode, 401);
      expect(error.message, 'The ID or password is not correct.');
    });

    testWidgets('a locked crew account says to ask the admin [CRW-ACC-07]', (tester) async {
      Object? error;
      try {
        await signInApi(tester, crew('R04', 5), scenarioPassword, role: 'crew');
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
    testWidgets(
      'the first MPIN is the last 6 digits and must be changed [AUTH-05, AUTH-12, AUTH-19]',
      (tester) async {
        await openSignIn(tester);
        final mobile = customer('C30');
        await enterIdAndPassword(tester, mobile, mobile.substring(4));

        // Nothing opens until the customer chooses an MPIN.
        await untilFound(tester, find.text('Choose your MPIN'));
        expect(find.byType(GreetingLine), findsNothing);

        Future<void> save(String first, String next, String confirm) async {
          await tester.enterText(find.byType(TextField).at(0), first);
          await tester.enterText(find.byType(TextField).at(1), next);
          await tester.enterText(find.byType(TextField).at(2), confirm);
          await tapFinder(tester, find.text('Save'));
        }

        await save(mobile.substring(4), '12345', '12345');
        await untilFound(tester, find.text('Use exactly 6 digits.'));
        await save(mobile.substring(4), '482915', '482916');
        await untilFound(tester, find.text('The two MPINs are not the same.'));
        await save(
          mobile.substring(4),
          mobile.substring(4),
          mobile.substring(4),
        );
        await untilFound(tester, find.textContaining('different'));

        await save(mobile.substring(4), '482915', '482915');
        // Signed in, and onboarding starts with the customer's details.
        await untilFound(tester, find.text('Step 1 of 7'));
        expect(find.text('Your details'), findsOneWidget);
        expect(find.byType(GreetingLine), findsNothing);
        await letTimersFinish(tester);
      },
    );
  });
}
