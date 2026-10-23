import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/ui/widgets.dart';
import 'package:priveo/features/crew/capture/media_capture.dart';
import 'package:priveo/features/crew/crew_text.dart';
import 'package:priveo/features/crew/home/crew_home_screen.dart';
import 'package:priveo/features/crew/job/job_card_screen.dart';

import 'support.dart';

PrimaryButton _markComplete(WidgetTester tester) => tester.widget<PrimaryButton>(
    find.widgetWithText(PrimaryButton, 'Save'));

Future<void> _openJob(WidgetTester tester) async {
  await tester.tap(find.text('MH12AB1234'));
  await tester.pumpAndSettle();
}

Future<void> _start(WidgetTester tester) async {
  await tester.tap(find.text(CrewText.startJob));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the home shows today\'s cards with no customer details',
      (tester) async {
    final backend = FakeCrewBackend();
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);

    expect(find.text('MH12AB1234'), findsOneWidget);
    expect(find.textContaining('B2-14'), findsWidgets);
    expect(find.text(CrewText.finishBy('7:00 AM')), findsWidgets);
    expect(find.text('Scheduled'), findsWidgets);
    // The fake's second job is on another crew member: not on this home.
    expect(find.text('MH12CD5678'), findsNothing);
    expect(find.text(CrewText.profile), findsNothing); // a tooltip only
    expect(backend.visitCalls.single, matches(r'^\d{4}-\d{2}-\d{2}$'));
  });

  testWidgets('the day can be moved and all jobs shown', (tester) async {
    final backend = FakeCrewBackend();
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);

    await tester.tap(find.byTooltip(CrewText.nextDay));
    await tester.pumpAndSettle();
    expect(backend.visitCalls, hasLength(2));
    expect(backend.visitCalls.last, isNot(backend.visitCalls.first));

    await tester.tap(find.text(CrewText.all));
    await tester.pumpAndSettle();
    expect(backend.visitCalls.last, 'all');
    expect(find.text(CrewText.allJobs), findsOneWidget);
  });

  testWidgets('a job cannot be marked complete until the checklist and proof '
      'are done', (tester) async {
    final backend = FakeCrewBackend();
    final capture = FakeCapture();
    await pumpCrew(tester, const CrewHomeScreen(),
        backend: backend, capture: capture);
    await _openJob(tester);
    expect(find.byType(JobCardScreen), findsOneWidget);
    expect(find.text('Hyundai Creta'), findsOneWidget);

    await _start(tester);
    expect(backend.jobs['j1']!.status, 'In progress');
    expect(_markComplete(tester).onPressed, isNull);
    expect(find.text('• 2 checklist items not checked'), findsOneWidget);

    await tester.tap(find.text('Item a'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Item b'));
    await tester.pumpAndSettle();
    // The checklist is done but there is no photo yet.
    expect(_markComplete(tester).onPressed, isNull);
    expect(find.text('• more photos to upload'), findsOneWidget);

    await tester.tap(find.text(CrewText.takePhoto));
    await tester.pumpAndSettle();
    expect(capture.photos, 1);
    expect(backend.sendCount, 1);
    expect(_markComplete(tester).onPressed, isNotNull);

    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(backend.jobs['j1']!.status, 'Completed');
    // Back on the job card, now closed.
    expect(find.text('Save'), findsNothing);
  });

  testWidgets('with no connection the photo waits and completion stays off',
      (tester) async {
    final backend = FakeCrewBackend();
    final queue = await pumpCrew(tester, const CrewHomeScreen(),
        backend: backend);
    await _openJob(tester);
    await _start(tester);
    await tester.tap(find.text('Item a'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Item b'));
    await tester.pumpAndSettle();

    backend.offline = true;
    await tester.tap(find.text(CrewText.takePhoto));
    await tester.pumpAndSettle();
    expect(queue.items, hasLength(1));
    expect(find.text(CrewText.waitingToSend), findsOneWidget);
    expect(_markComplete(tester).onPressed, isNull);
    expect(find.textContaining('1 upload waiting to send'), findsWidgets);

    // The connection returns and the queue sends it.
    backend.offline = false;
    await queue.drain();
    await tester.pumpAndSettle();
    expect(queue.items, isEmpty);
    expect(_markComplete(tester).onPressed, isNotNull);
  });

  testWidgets('a file that breaks the rules is not queued', (tester) async {
    final backend = FakeCrewBackend();
    final capture = FakeCapture()
      ..next = const CapturedFile(
          path: '/tmp/big.jpg',
          contentType: 'image/jpeg',
          sizeBytes: maxPhotoBytes + 1,
          video: false);
    final queue = await pumpCrew(tester, const CrewHomeScreen(),
        backend: backend, capture: capture);
    await _openJob(tester);
    await _start(tester);

    await tester.tap(find.text(CrewText.takePhoto));
    await tester.pumpAndSettle();
    expect(find.text(CrewText.photoTooLarge), findsOneWidget);
    expect(queue.items, isEmpty);
  });

  testWidgets('could not complete needs a reason and records it',
      (tester) async {
    final backend = FakeCrewBackend();
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);
    await _openJob(tester);

    await tester.tap(find.text(CrewText.couldNotComplete));
    await tester.pumpAndSettle();
    PrimaryButton confirm() => tester.widget<PrimaryButton>(
        find.widgetWithText(PrimaryButton, 'Save'));
    expect(confirm().onPressed, isNull);

    await tester.tap(find.text('Car is locked'));
    await tester.pumpAndSettle();
    // A reason alone is not enough: the remark is required.
    expect(confirm().onPressed, isNull);
    await tester.enterText(find.byType(TextField), 'No one around');
    await tester.pump();
    expect(confirm().onPressed, isNotNull);
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(backend.couldNot['j1'],
        {'reason': 'car_locked', 'note': 'No one around', 'upload': null});
    expect(backend.jobs['j1']!.status, 'Could not complete');
    // Back on the job card: closed, with the reason shown.
    expect(find.widgetWithText(OutlinedButton, CrewText.couldNotComplete),
        findsNothing);
    expect(find.text('Car is locked'), findsOneWidget);
  });

  testWidgets('a Manager sees the team and can reassign and skip a job',
      (tester) async {
    final backend = FakeCrewBackend(role: 'Manager');
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);

    await tester.tap(find.byTooltip(CrewText.team));
    await tester.pumpAndSettle();
    expect(find.text('Ravi Kumar'), findsOneWidget);
    expect(find.text('Sunil'), findsOneWidget);

    await tester.tap(find.text('Ravi Kumar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('MH12AB1234'));
    await tester.pumpAndSettle();

    await tester.tap(find.text(CrewText.reassign));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('assign-c2')));
    await tester.pumpAndSettle();
    expect(backend.reassigned, {'j1': 'c2'});

    await tester.tap(find.text(CrewText.skipJob));
    await tester.pumpAndSettle();
    await tester.tap(find.descendant(
        of: find.byType(AlertDialog),
        matching: find.widgetWithText(TextButton, CrewText.skipJob)));
    await tester.pumpAndSettle();
    expect(backend.skipped, ['j1']);
  });

  testWidgets('a Manager marks a crew member absent and sees the jobs moved',
      (tester) async {
    final backend = FakeCrewBackend(role: 'Manager');
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);
    await tester.tap(find.byTooltip(CrewText.team));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip(CrewText.attendance));
    await tester.pumpAndSettle();
    expect(find.text('Sunil'), findsOneWidget);

    await tester.tap(find.text('Sunil'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('attendance-Sick')));
    await tester.pumpAndSettle();
    expect(backend.attendanceSet, {'c2': 'Sick'});
    expect(find.textContaining('1 job needs scheduling'), findsOneWidget);
    // The list shows the new status.
    expect(find.text(CrewText.attendanceSick), findsOneWidget);
  });

  testWidgets('a Manager changes working hours for a crew member',
      (tester) async {
    final backend = FakeCrewBackend(role: 'Manager');
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);
    await tester.tap(find.byTooltip(CrewText.team));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip(CrewText.workingHours));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('hours-c2')));
    await tester.pumpAndSettle();

    // Turn Monday off and save.
    await tester.tap(find.descendant(
        of: find.byKey(const ValueKey('hours-day-Monday')),
        matching: find.byType(Switch)));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(PrimaryButton, CrewText.save));
    await tester.pumpAndSettle();
    final saved = backend.hoursSet['c2']!;
    expect(saved.first.day, 'Monday');
    expect(saved.first.working, isFalse);
    expect(saved[1].working, isTrue);
    expect(find.text(CrewText.hoursSaved), findsOneWidget);
  });

  testWidgets('reassign shows why a crew member cannot take the job',
      (tester) async {
    final backend = FakeCrewBackend(role: 'Manager')
      ..blockedReassign['c2'] = 'Is away that day (Leave).';
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);
    await tester.tap(find.byTooltip(CrewText.team));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ravi Kumar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('MH12AB1234'));
    await tester.pumpAndSettle();
    await tester.tap(find.text(CrewText.reassign));
    await tester.pumpAndSettle();

    expect(find.textContaining('Is away that day (Leave).'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('assign-c2')));
    await tester.pumpAndSettle();
    expect(backend.reassigned, isEmpty);
  });

  testWidgets('a Member has no team button', (tester) async {
    await pumpCrew(tester, const CrewHomeScreen(), backend: FakeCrewBackend());
    expect(find.byTooltip(CrewText.team), findsNothing);
    expect(find.byTooltip(CrewText.profile), findsOneWidget);
  });

  testWidgets('the profile shows the crew member\'s own details',
      (tester) async {
    await pumpCrew(tester, const CrewHomeScreen(), backend: FakeCrewBackend());
    await tester.tap(find.byTooltip(CrewText.profile));
    await tester.pumpAndSettle();
    expect(find.text('Ravi Kumar'), findsOneWidget);
    expect(find.text('9000000002'), findsOneWidget);
    expect(find.text('Mon 06:00 - 14:00'), findsOneWidget);
    expect(find.text('Member'), findsOneWidget);
  });
}
