// Customer actions that change data, on the real screens against the real
// fixture API: paying by UPI, reading notifications, replying to a complaint,
// the monthly check-in, feedback, and the password form (PAY, NOTIF, CMP,
// CHK, FDBK, ACC). Each test uses its own scenario, so none depends on
// another. Needs the fixture API; see scenario_screens_test.dart.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/ui/widgets.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';
import 'package:priveo/features/support/widgets.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario customer actions', () {}, skip: 'SCENARIO_API_URL not set');
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

  Future<void> tapStar(WidgetTester tester, int n) async {
    final stars = find.descendant(
      of: find.byType(StarRating).first,
      matching: find.byType(InkWell),
    );
    await tester.ensureVisible(stars.at(n - 1));
    await tester.tap(stars.at(n - 1));
    await tester.pump(const Duration(milliseconds: 300));
  }

  group('payment', () {
    testWidgets('C09 says it has paid; Priveo then shows it as Initiated', (
      tester,
    ) async {
      await home(tester, 'C09');
      await tapFinder(tester, find.text('My subscription'));
      await tapFinder(tester, find.text('Renew subscription'));
      await tapFinder(tester, find.text("I've paid"));

      await untilFound(tester, find.text('Payment submitted'));
      expect(find.text('Initiated'), findsWidgets);
      expect(
        find.textContaining('Priveo will confirm your payment of ₹999'),
        findsOneWidget,
      );
      expect(find.text('Go to home'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });

  group('notifications', () {
    testWidgets('C29 marks all notifications as read', (tester) async {
      await home(tester, 'C29');
      await tapFinder(tester, find.text('Account'));
      await tapFinder(tester, find.text('Notifications'));
      await untilFound(tester, find.text('Mark all as read'));

      await tapFinder(tester, find.text('Mark all as read'));
      await until(
        tester,
        () => find.text('Mark all as read').evaluate().isEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(find.text('Mark all as read'), findsNothing);
      // Both messages stay in the list.
      expect(find.text('TEST Unread service message'), findsOneWidget);
      expect(find.text('TEST Read service message'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });

  group('complaints', () {
    testWidgets('C12 opens a raised complaint and replies on it', (
      tester,
    ) async {
      await home(tester, 'C12');
      await tapFinder(tester, find.text('Support'));
      await tapFinder(tester, find.text('My complaints'));
      await tapFinder(tester, find.text('#C-1200'));

      // The reply box is the sign that the detail page, not the list, is open.
      await untilFound(tester, find.text('Write a reply'));
      expect(find.text('Synthetic Raised complaint'), findsWidgets);
      expect(find.text('Raised'), findsWidgets);
      expect(find.text('Synthetic thread entry'), findsWidgets);

      await typeIntoLastField(tester, 'Still dusty today.');
      await tapFinder(tester, find.text('Send'));
      // The reply joins the thread; the form clears.
      await until(
        tester,
        () =>
            find.text('Still dusty today.').evaluate().length == 1 &&
            find.text('Synthetic thread entry').evaluate().isNotEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(find.text('Still dusty today.'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });

  group('check-in and feedback', () {
    testWidgets('C23 submits its monthly check-in', (tester) async {
      await home(tester, 'C23');
      await tapFinder(tester, find.text('Monthly check-in'));
      await untilFound(tester, find.byType(StarRating));
      expect(find.text('Likelihood to recommend'), findsOneWidget);

      // CHK-07: nothing can be submitted until one category is rated.
      final submit = find.widgetWithText(PrimaryButton, 'Submit');
      await scrollTo(tester, submit);
      expect(tester.widget<PrimaryButton>(submit).onPressed, isNull);

      await tapStar(tester, 5);
      await typeIntoLastField(tester, 'Works well.');
      await tapFinder(tester, submit);
      await untilFound(tester, find.text('Thank you. Your check-in is saved.'));
      await letTimersFinish(tester);
    });

    testWidgets('C09 sends feedback from the side tab', (tester) async {
      await home(tester, 'C09');
      await tapFinder(tester, find.byIcon(Symbols.feedback_rounded));
      await untilFound(tester, find.text('Your rating'));
      await until(
        tester,
        () => find.text('Exterior finish').evaluate().isNotEmpty,
        timeout: const Duration(seconds: 6),
      );
      expect(
        find.text('Exterior finish'),
        findsWidgets,
        reason: visibleTexts().join(' | '),
      );

      await tapStar(tester, 4);
      await tapFinder(tester, find.text('Send'));
      await untilFound(tester, find.text('Thank you for your feedback.'));
      await letTimersFinish(tester);
    });
  });

  group('password', () {
    testWidgets('C25 is told when the form or the current password is wrong', (
      tester,
    ) async {
      await home(tester, 'C25');
      await tapFinder(tester, find.text('Account'));
      await tapFinder(tester, find.text('Change password'));
      await untilFound(tester, find.text('Current password'));

      const rule = 'Use at least 8 characters, with a letter and a number.';
      // The rule is a hint; after a bad save it shows again as the error.
      expect(find.text(rule), findsOneWidget);
      await tapFinder(tester, find.text('Save'));
      expect(find.text(rule), findsNWidgets(2));

      await tester.enterText(find.byType(TextField).at(0), 'wrong-current-1');
      await tester.enterText(find.byType(TextField).at(1), 'abc');
      await tapFinder(tester, find.text('Save'));
      expect(find.text(rule), findsNWidgets(2));
      expect(find.text('The current password is not correct.'), findsNothing);

      // A valid new password with the wrong current one is refused by the API.
      await tester.enterText(find.byType(TextField).at(1), 'NewPassword123');
      await tapFinder(tester, find.text('Save'));
      await untilFound(
        tester,
        find.text('The current password is not correct.'),
      );
      await letTimersFinish(tester);
    });
  });
}
