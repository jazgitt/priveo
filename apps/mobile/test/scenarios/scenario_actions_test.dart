// Action flows on the real screens against the real fixture API: the test
// taps through the screen, the API changes its data, and the screen shows the
// result. Each test uses its own scenario so the tests do not depend on order.
// Needs the fixture API; see scenario_screens_test.dart for how to run.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario actions', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }
  setUpAll(() => HttpOverrides.global = null);
  final scenarios = loadScenarios();
  String customer(String id) => scenarios[id]!['customer_login'] as String;

  Future<void> home(WidgetTester tester, String id) async {
    await openApp(
      tester,
      await signInApi(tester, customer(id), scenarioPassword),
    );
    await untilFound(tester, find.byType(GreetingLine));
  }

  group('report an issue', () {
    testWidgets('C09 reports a problem and sees it raised', (tester) async {
      await home(tester, 'C09');
      await tapFinder(tester, find.text('Report an Issue'));
      await untilFound(tester, find.text('What went wrong?'));

      // ISS-05: a category is required.
      await tapFinder(tester, find.text('Send report'));
      expect(find.text('Choose what went wrong.'), findsOneWidget);

      await tapFinder(tester, find.byType(ChoiceChip));
      await tester.enterText(
        find.byType(TextField).last,
        'The bonnet was left dusty.',
      );
      await tapFinder(tester, find.text('Send report'));
      // The app opens the new complaint, as Raised, with what was typed.
      // (The typed text also sits in the form field until the screen changes.)
      await untilFound(tester, find.text('Raised'));
      expect(find.text('The bonnet was left dusty.'), findsWidgets);
      expect(find.text('Cleaning quality'), findsWidgets);
      await letTimersFinish(tester);
    });
  });

  group('skip and pause', () {
    Future<void> openSkipPause(WidgetTester tester, String id) async {
      await home(tester, id);
      await tapFinder(tester, find.text('Skip or Pause'));
      await untilFound(tester, find.text('Confirm skip'));
    }

    testWidgets('C03 skips a day and undoes it', (tester) async {
      await openSkipPause(tester, 'C03');

      // A date must be picked first.
      await tapFinder(tester, find.text('Confirm skip'));
      expect(find.text('Pick a date to skip first.'), findsOneWidget);

      await tapFinder(tester, find.text('Exterior').first);
      await tapFinder(tester, find.text('Confirm skip'));
      await untilFound(tester, find.text('Skipped'));

      // Choosing the skipped day offers to undo it.
      await tapFinder(tester, find.text('Skipped').first);
      await tapFinder(tester, find.text('Undo skip'));
      await until(
        tester,
        () => find.text('Skipped').evaluate().isEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(
        find.text('Skipped'),
        findsNothing,
        reason: visibleTexts().join(' | '),
      );
      await letTimersFinish(tester);
    });

    testWidgets('C04 pauses for dates and ends the pause', (tester) async {
      await openSkipPause(tester, 'C04');
      await tapFinder(tester, find.text('Pause'));

      // Both dates are needed.
      await tapFinder(tester, find.text('Confirm pause'));
      expect(
        find.text('Choose the start and end dates first.'),
        findsOneWidget,
      );

      await tapFinder(tester, find.textContaining('From'));
      await tapFinder(tester, find.text('OK'));
      await tapFinder(tester, find.textContaining('To:'));
      await tapFinder(tester, find.text('OK'));
      await tapFinder(tester, find.text('Confirm pause'));
      await untilFound(tester, find.textContaining('Plan now renews'));
      expect(find.textContaining('Paused '), findsWidgets);

      // The pause is listed with a way to end it.
      await tapFinder(tester, find.text('End pause'));
      await untilFound(
        tester,
        find.text('The pause has ended. Visits resume.'),
      );
      await letTimersFinish(tester);
    });
  });

  group('Deep Spa', () {
    testWidgets('C05 books a spa date and reaches the payment', (tester) async {
      await home(tester, 'C05');
      await tapFinder(tester, find.text('Deep Spa'));
      await untilFound(tester, find.text('Confirm & pay'));

      // A date must be chosen first.
      await tapFinder(tester, find.text('Confirm & pay'));
      await untilFound(tester, find.text('Choose a date'));

      await tapFinder(tester, find.textContaining('Preferred date'));
      await tapFinder(tester, find.text('OK'));
      await untilFound(tester, find.textContaining('Preferred date: 1'));
      // The date the picker chose, as the screen shows it (dd-Mon-yy).
      final chosen = RegExp(
        r'Preferred date: (\d{2}-\w{3}-\d{2})',
      ).firstMatch(visibleTexts().join(' | '))!.group(1)!;
      await tapFinder(tester, find.text('Confirm & pay'));

      // The request is created and listed under "Your requests".
      await until(
        tester,
        () => find.textContaining('Deep Spa, $chosen').evaluate().isNotEmpty,
        timeout: const Duration(seconds: 10),
      );
      expect(
        find.textContaining('Deep Spa, $chosen'),
        findsOneWidget,
        reason: visibleTexts().join(' | '),
      );
      await letTimersFinish(tester);
    });
  });
}
