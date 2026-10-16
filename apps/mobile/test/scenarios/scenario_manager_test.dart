// Crew Manager flows on the real screens against the real fixture API: the
// team and its jobs, attendance, and a team member's job card with its manager
// actions (CRW-MGR). R01's Manager leads a Member with five jobs and a
// Trainee; R03's Manager leads a team with sick, leave and late-start members.
// Needs the fixture API; see scenario_screens_test.dart.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario manager', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }
  setUpAll(() => HttpOverrides.global = null);
  final scenarios = loadScenarios();
  String crew(String id, int i) =>
      (scenarios[id]!['crew_logins'] as List)[i] as String;

  Future<void> teamScreen(WidgetTester tester, String id) async {
    await openApp(
      tester,
      await signInApi(tester, crew(id, 0), scenarioPassword),
    );
    await untilFound(tester, find.text('Total'));
    await untilFound(tester, find.byTooltip('Team'));
    await tester.tap(find.byTooltip('Team').first);
    await tester.pump(const Duration(milliseconds: 400));
    await untilFound(tester, find.text('Team'));
  }

  group('team', () {
    testWidgets('a Member and a Trainee do not see the team', (tester) async {
      await openApp(
        tester,
        await signInApi(tester, crew('R01', 1), scenarioPassword),
      );
      await untilFound(tester, find.text('TS30TT0001'));
      expect(find.byTooltip('Team'), findsNothing);
      await letTimersFinish(tester);
    });

    testWidgets('R01 Manager sees each member and how many jobs they have', (
      tester,
    ) async {
      await teamScreen(tester, 'R01');
      await untilFound(tester, find.text('Member · 5 jobs'));
      expect(find.text('Manager · 0 jobs'), findsOneWidget);
      expect(find.text('Trainee · 0 jobs'), findsOneWidget);
      expect(find.text('TEST R01 Member 1'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('opening a member lists their jobs with every state', (
      tester,
    ) async {
      await teamScreen(tester, 'R01');
      await tapFinder(tester, find.text('TEST R01 Member 1'));
      await untilFound(tester, find.text('TS30TT0001'));
      for (final plate in [
        'TS30TT0001',
        'TS30TT0002',
        'TS30TT0003',
        'TS30TT0004',
        'TS30TT0005',
      ]) {
        expect(find.text(plate), findsOneWidget, reason: plate);
      }
      for (final state in [
        'Scheduled',
        'In progress',
        'Completed',
        'Skipped',
        'Could not complete',
      ]) {
        expect(find.text(state), findsWidgets, reason: state);
      }
      await letTimersFinish(tester);
    });
  });

  group('attendance', () {
    testWidgets('R03 shows present, sick, leave and a late start', (
      tester,
    ) async {
      await teamScreen(tester, 'R03');
      await untilFound(tester, find.byTooltip('Attendance'));
      await tester.tap(find.byTooltip('Attendance').first);
      await tester.pump(const Duration(milliseconds: 400));

      await untilFound(tester, find.text('Sick'));
      expect(find.text('Present'), findsWidgets);
      expect(find.text('Leave'), findsOneWidget);
      expect(find.text('Late start, from 08:00'), findsOneWidget);
      expect(find.text('Member · 05:00 - 14:00'), findsWidgets);
      await letTimersFinish(tester);
    });
  });

  group('a team member job', () {
    testWidgets(
      'a scheduled job offers reassign, could not complete and skip',
      (tester) async {
        await teamScreen(tester, 'R01');
        await tapFinder(tester, find.text('TEST R01 Member 1'));
        await tapFinder(tester, find.text('TS30TT0001'));

        await untilFound(tester, find.text('Reassign'));
        expect(find.text('Could not complete'), findsWidgets);
        expect(find.text('Skip job'), findsOneWidget);
        expect(find.text('TEST R01 Member 1'), findsWidgets);
        await letTimersFinish(tester);
      },
    );
  });
}
