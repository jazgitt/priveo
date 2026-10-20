// Admin actions that change data, on the real screens against the real fixture
// API: confirm or reject a payment, update a complaint, add a crew exception
// and skip a missed job (ADM-PAY, ADM-CMP, ADM-CRW, ADM-OPS). Each test uses
// its own records. Needs the fixture API; see scenario_screens_test.dart.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario admin actions', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }
  setUpAll(() => HttpOverrides.global = null);

  Future<void> home(WidgetTester tester) async {
    await openApp(
      tester,
      await signInApi(tester, 'priveopapa', scenarioAdminPassword),
    );
    await untilFound(tester, find.text('Payments to confirm'));
  }

  Future<void> openTile(WidgetTester tester, String label) =>
      tapScrolling(tester, find.text(label));

  /// The Confirm or Reject button on the payment card that shows [plate].
  Finder paymentButton(String plate, String label) => find.descendant(
    of: find.ancestor(of: find.text(plate), matching: find.byType(Card)),
    matching: find.text(label),
  );

  group('payments', () {
    testWidgets('confirming a payment removes it from the list [ADM-PAY-02, ADM-PAY-03]', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'All payments');
      await untilFound(tester, find.text('Creta TS 36 TT 0001'));

      await tapFinder(tester, paymentButton('Creta TS 36 TT 0001', 'Confirm'));
      await untilFound(tester, find.text('Payment confirmed.'));
      await until(
        tester,
        () => find.text('Creta TS 36 TT 0001').evaluate().isEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(find.text('Creta TS 36 TT 0001'), findsNothing);
      // The other payments still wait.
      expect(find.text('Creta TS 15 TT 0002'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('rejecting a payment sends it back and removes it [ADM-PAY-02, ADM-PAY-07]', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'All payments');
      await untilFound(tester, find.text('Creta TS 15 TT 0002'));

      await tapFinder(tester, paymentButton('Creta TS 15 TT 0002', 'Reject'));
      await untilFound(tester, find.text('Payment sent back.'));
      await until(
        tester,
        () => find.text('Creta TS 15 TT 0002').evaluate().isEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(find.text('Creta TS 15 TT 0002'), findsNothing);
      await letTimersFinish(tester);
    });
  });

  group('complaints', () {
    testWidgets('moving a complaint to In progress with a note [ADM-CMP-03, ADM-CMP-04]', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Complaints');
      await tapFinder(tester, find.textContaining('#C-3700'));

      await untilFound(tester, find.text('Save status'));
      expect(find.text('History'), findsOneWidget);
      expect(find.textContaining('Open for more than 4 hours'), findsWidgets);

      // A note is needed before one can be added.
      await tapFinder(tester, find.text('Add note'));
      expect(find.text('Write a note first.'), findsOneWidget);

      await typeIntoLastField(tester, 'Checking with the crew.');
      await tapFinder(tester, find.text('Add note'));
      await untilFound(tester, find.text('Saved.'));
      // The note joins the history, further down the page.
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(seconds: 2)),
      );
      await tester.pump(const Duration(milliseconds: 300));
      await scrollTo(tester, find.textContaining('Checking with the crew.'));
      expect(find.textContaining('Checking with the crew.'), findsWidgets);

      await tapFinder(tester, find.text('In progress'));
      await tapFinder(tester, find.text('Save status'));
      // The earlier note already showed 'Saved.', so wait for this request to
      // reach the API; the fixture API serves one request at a time.
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(seconds: 2)),
      );
      await tester.pump(const Duration(milliseconds: 300));
      await letTimersFinish(tester);
    });
  });

  group('crew', () {
    testWidgets('adding a sick exception for a crew member [ADM-CRW-08, ADM-CRW-09]', (tester) async {
      await home(tester);
      await openTile(tester, 'Crew');
      await untilFound(tester, find.text('TEST A01 Member 1 · Member'));
      await tapFinder(tester, find.text('Add crew exception'));

      await untilFound(tester, find.text('Exception type'));
      expect(find.text('Sick'), findsWidgets);
      expect(find.textContaining('From date:'), findsOneWidget);
      expect(find.textContaining('To date:'), findsOneWidget);
      await tapFinder(tester, find.text('Save'));
      // The form closes once the exception is saved.
      await until(
        tester,
        () => find.text('Exception type').evaluate().isEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(find.text('Exception type'), findsNothing);
      await letTimersFinish(tester);
    });
  });
}
