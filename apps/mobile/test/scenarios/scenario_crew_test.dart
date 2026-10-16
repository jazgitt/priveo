// Crew flows on the real screens against the real fixture API. R01's Member
// has four jobs today: Scheduled, In progress, Completed and Could not
// complete (CRW-SCH, CRW-SVC). Photo and video capture need the device
// plugins, so "Mark complete" is checked only for what blocks it.
// Needs the fixture API; see scenario_screens_test.dart for how to run.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario crew', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }
  setUpAll(() => HttpOverrides.global = null);
  final scenarios = loadScenarios();
  String crew(String id, int i) =>
      (scenarios[id]!['crew_logins'] as List)[i] as String;

  final couldNotCompleteButton = find.widgetWithText(
    OutlinedButton,
    'Could not complete',
  );

  Future<void> member(WidgetTester tester) async {
    await openApp(
      tester,
      await signInApi(tester, crew('R01', 1), scenarioPassword),
    );
    await untilFound(tester, find.text('TS30TT0001'));
  }

  group('day list', () {
    testWidgets('R01 Member sees the four jobs and their states', (
      tester,
    ) async {
      await member(tester);
      for (final plate in [
        'TS30TT0001',
        'TS30TT0002',
        'TS30TT0003',
        'TS30TT0005',
      ]) {
        expect(find.text(plate), findsOneWidget);
      }
      for (final state in [
        'Scheduled',
        'In progress',
        'Completed',
        'Could not complete',
      ]) {
        expect(find.text(state), findsWidgets, reason: 'state "$state"');
      }
      // Four jobs, two of them done.
      expect(find.text('Total'), findsOneWidget);
      expect(find.text('Done'), findsOneWidget);
      expect(find.text('Left'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('R02 has an empty day', (tester) async {
      await openApp(
        tester,
        await signInApi(tester, crew('R02', 0), scenarioPassword),
      );
      await untilFound(tester, find.text('No jobs for this day.'));
      await letTimersFinish(tester);
    });
  });

  group('job card', () {
    testWidgets('a completed job shows when it finished and has no actions', (
      tester,
    ) async {
      await member(tester);
      await tapFinder(tester, find.text('TS30TT0003'));
      await untilFound(tester, find.textContaining('Finished on'));
      expect(find.text('Start job'), findsNothing);
      expect(find.text('Continue'), findsNothing);
      expect(couldNotCompleteButton, findsNothing);
      expect(find.text('5 / 5'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('a job that could not be completed shows why', (tester) async {
      await member(tester);
      await tapFinder(tester, find.text('TS30TT0005'));
      await untilFound(tester, find.text('Car not in the parking spot'));
      expect(find.text('Synthetic operational outcome'), findsOneWidget);
      expect(find.text('Start job'), findsNothing);
      await letTimersFinish(tester);
    });

    testWidgets('a scheduled job offers Start job and Could not complete', (
      tester,
    ) async {
      await member(tester);
      await tapFinder(tester, find.text('TS30TT0001'));
      await untilFound(tester, find.text('Start job'));
      expect(couldNotCompleteButton, findsOneWidget);
      expect(find.text('0 / 5'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });

  group('doing a job', () {
    testWidgets(
      'starting a job opens its checklist; ticking updates what is missing',
      (tester) async {
        await member(tester);
        await tapFinder(tester, find.text('TS30TT0001'));
        await tapFinder(tester, find.text('Start job'));

        await untilFound(tester, find.text('Exterior body cleaned'));
        expect(find.text('Final inspection completed'), findsOneWidget);
        // Nothing can be completed yet: the missing items are listed.
        expect(find.text('Before you can mark this complete:'), findsOneWidget);
        expect(find.text('• 5 checklist items not checked'), findsOneWidget);
        expect(find.text('• 2 more photos to upload'), findsOneWidget);
        expect(find.text('• 1 more video to upload'), findsOneWidget);

        await tapFinder(tester, find.text('Exterior body cleaned'));
        await untilFound(tester, find.text('• 4 checklist items not checked'));
        await letTimersFinish(tester);
      },
    );

    testWidgets('a scheduled or in-progress job can be opened to perform', (
      tester,
    ) async {
      await member(tester);
      await tapFinder(tester, find.text('TS30TT0001'));
      // R01's other tests may already have started it; either way the card
      // offers Start job or Continue and opens the perform screen.
      final start = find.text('Start job');
      final cont = find.text('Continue');
      await until(
        tester,
        () => start.evaluate().isNotEmpty || cont.evaluate().isNotEmpty,
      );
      await tapFinder(tester, start.evaluate().isNotEmpty ? start : cont);
      await untilFound(tester, find.text('Perform service'));
      await letTimersFinish(tester);
    });

    testWidgets('could not complete needs a reason, then marks the job', (
      tester,
    ) async {
      await member(tester);
      await tapFinder(tester, find.text('TS30TT0002'));
      await tapFinder(tester, couldNotCompleteButton);
      await untilFound(tester, find.text('Car is locked'));

      // Nothing is sent until a reason is chosen.
      await tapFinder(tester, find.text('Car is locked'));
      await tester.enterText(find.byType(TextField), 'Gate was locked.');
      await tapFinder(tester, find.text('Confirm'));

      // Back on the job card, which now shows the outcome and no actions.
      await untilFound(tester, find.text('Gate was locked.'));
      expect(find.text('Car is locked'), findsOneWidget);
      expect(find.text('Continue'), findsNothing);
      expect(couldNotCompleteButton, findsNothing);
      await letTimersFinish(tester);
    });
  });
}
