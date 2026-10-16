// Admin quick actions on the real screens against the real fixture API:
// payments to confirm, complaints, ratings, the day schedule, capacity,
// customers, crew, add-ons and operations outcomes (the Admin mobile subset of
// ADM-PAY, ADM-CMP, ADM-FDB, ADM-SCH, ADM-CAP, ADM-CUS, ADM-CRW, ADM-ADD,
// ADM-OPS). Needs the fixture API; see scenario_screens_test.dart.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario admin', () {}, skip: 'SCENARIO_API_URL not set');
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

  /// Opens a tile on the Admin home. The home is a long list, so the tile may
  /// need scrolling into view.
  Future<void> openTile(WidgetTester tester, String label) =>
      tapScrolling(tester, find.text(label));

  group('home', () {
    testWidgets('shows the counts, the payments waiting and the entries', (
      tester,
    ) async {
      await home(tester);
      for (final label in ['Alerts', 'Needs scheduling', 'Open complaints']) {
        expect(find.text(label), findsWidgets, reason: label);
      }
      // The first payments waiting are listed on the home itself.
      expect(find.text('Test C08, Flat TEST-101'), findsOneWidget);
      expect(find.text('Test C09, Flat TEST-101'), findsOneWidget);
      for (final label in [
        'Operations',
        'Customers',
        'Crew',
        'Add-on requests',
        'Monthly check-in results',
      ]) {
        expect(find.text(label), findsWidgets, reason: label);
      }
      await letTimersFinish(tester);
    });
  });

  group('payments', () {
    testWidgets('lists every payment to confirm with Reject and Confirm', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'All payments');
      await untilFound(tester, find.text('Plan: TEST plan cycle'));
      expect(find.text('Add-on: Deep Spa'), findsOneWidget);
      expect(find.text('Confirm'), findsNWidgets(4));
      expect(find.text('Reject'), findsNWidgets(4));
      await letTimersFinish(tester);
    });
  });

  group('complaints', () {
    testWidgets('lists complaints with a status filter and an overdue mark', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Complaints');
      await untilFound(tester, find.textContaining('#C-3700'));
      for (final status in ['All', 'Raised', 'In progress', 'Resolved']) {
        expect(find.text(status), findsWidgets, reason: 'filter "$status"');
      }
      // ADM-CMP-06: a raised complaint older than 4 hours is marked.
      expect(find.textContaining('Open for more than 4 hours'), findsWidgets);
      await letTimersFinish(tester);
    });
  });

  group('ratings and check-ins', () {
    testWidgets('shows the average rating and its stars filter', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Feedback and ratings');
      await untilFound(tester, find.text('Average 4.0 from 6 ratings'));
      expect(find.text('Visit ratings'), findsOneWidget);
      for (final stars in ['5 stars', '4 stars', '3 stars']) {
        expect(find.text(stars), findsWidgets, reason: stars);
      }
      await letTimersFinish(tester);
    });

    testWidgets('shows the monthly check-in results', (tester) async {
      await home(tester);
      await openTile(tester, 'Monthly check-in results');
      await untilFound(tester, find.textContaining('Value for money'));
      expect(find.text('Synthetic check-in'), findsWidgets);
      await letTimersFinish(tester);
    });
  });

  group('scheduling', () {
    testWidgets('the day schedule counts the jobs and shows the crew rows', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Day schedule');
      await untilFound(tester, find.text('10 jobs, 4 done, 4 left'));
      expect(find.text('Schedule: Frozen'), findsOneWidget);
      expect(find.text('TEST A03 Member 1'), findsOneWidget);
      expect(find.text('TEST R01 Member 1'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('capacity shows crew minutes against work for each day', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Capacity');
      await untilFound(
        tester,
        find.text('Crew 1080 min, work 40 min, placed 0 min'),
      );
      await letTimersFinish(tester);
    });
  });

  group('customers, crew and add-ons', () {
    testWidgets('customer search narrows the list', (tester) async {
      await home(tester);
      await openTile(tester, 'Customers');
      await untilFound(tester, find.text('Test A01'));
      await typeIntoLastField(tester, 'C12');
      await until(
        tester,
        () => find.text('Test A01').evaluate().isEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(find.text('Test A01'), findsNothing);
      expect(find.text('Test C12'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('the crew list shows roles and an exception action', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Crew');
      await untilFound(tester, find.text('TEST A01 Manager 0 · Manager'));
      expect(find.text('TEST A01 Member 1 · Member'), findsOneWidget);
      expect(find.text('TEST A01 Trainee 2 · Trainee'), findsOneWidget);
      expect(find.text('Add crew exception'), findsWidgets);
      await letTimersFinish(tester);
    });

    testWidgets('add-on requests show their statuses and payments', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Add-on requests');
      await untilFound(tester, find.text('Status filter'));
      await untilFound(tester, find.textContaining('Deep Spa · '));
      expect(find.textContaining('Missed'), findsWidgets);
      expect(find.textContaining('Completed'), findsWidgets);
      expect(find.textContaining('₹1,500'), findsWidgets);
      await letTimersFinish(tester);
    });
  });

  group('operations', () {
    testWidgets('the missed queue offers a skip only with a reason', (
      tester,
    ) async {
      await home(tester);
      await openTile(tester, 'Operations');
      await untilFound(tester, find.text('Missed jobs'));
      await untilFound(tester, find.textContaining('TS30TT0005'));
      expect(
        find.text('Car not in the parking spot Synthetic operational outcome'),
        findsWidgets,
      );
      expect(find.text('Skip job by operations'), findsWidgets);
      expect(
        find.textContaining(
          'Skipping adds one day to the plan and moves unpaid renewal dates.',
        ),
        findsWidgets,
      );
      await letTimersFinish(tester);
    });
  });
}
