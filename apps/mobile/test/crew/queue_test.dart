import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/features/feature_flags.dart';
import 'package:priveo/core/features/feature_keys.dart';
import 'package:priveo/features/crew/crew_text.dart';
import 'package:priveo/features/crew/data/crew_models.dart';
import 'package:priveo/features/crew/home/crew_home_screen.dart';
import 'package:priveo/features/crew/job/job_card_screen.dart';

import 'support.dart';

/// Two jobs of the same crew member: the first is current, the second locked
/// behind it until the first is closed (S-13, C-01, C-02).
class QueueBackend extends FakeCrewBackend {
  QueueBackend() {
    jobs['j2']!.assignedTo = null;
  }

  @override
  Future<CrewVisitList> visits({DateTime? date, bool all = false}) async {
    visitCalls.add(all ? 'all' : 'day');
    var firstOpen = true;
    final cards = <CrewJobCard>[];
    for (final j in jobs.values) {
      final closed = JobStatus.isClosed(j.status);
      final current = !closed && firstOpen;
      final locked = !closed && !firstOpen;
      if (!closed) firstOpen = false;
      cards.add(CrewJobCard.fromJson(cardJson(
          id: j.id,
          status: j.status,
          registration: j.registration,
          locked: locked,
          current: current)));
    }
    final done = cards.where((c) => c.isClosed).length;
    return CrewVisitList(
        date: date,
        society: 'Green Meadows',
        total: cards.length,
        done: done,
        left: cards.length - done,
        jobs: cards);
  }
}

class _QueueOff extends FeatureFlagsController {
  @override
  FeatureFlags build() =>
      const FeatureFlags(flags: {FeatureKeys.sequentialQueue: false});
}

void main() {
  testWidgets('a locked row is disabled with a lock and names the vehicle to '
      'finish first', (tester) async {
    await pumpCrew(tester, const CrewHomeScreen(), backend: QueueBackend());

    expect(find.byKey(const ValueKey('queue-lock')), findsOneWidget);
    expect(find.text('Finish MH12AB1234 first'), findsOneWidget);
    await tester.tap(find.text('MH12CD5678'));
    await tester.pumpAndSettle();
    expect(find.byType(JobCardScreen), findsNothing);

    await tester.tap(find.text('MH12AB1234'));
    await tester.pumpAndSettle();
    expect(find.byType(JobCardScreen), findsOneWidget);
  });

  testWidgets('with the flag off the old list shows without locks',
      (tester) async {
    await pumpCrew(tester, const CrewHomeScreen(),
        backend: QueueBackend(),
        extra: [featureFlagsProvider.overrideWith(_QueueOff.new)]);

    expect(find.byKey(const ValueKey('queue-lock')), findsNothing);
    expect(find.textContaining('Finish MH12'), findsNothing);
    await tester.tap(find.text('MH12CD5678'));
    await tester.pumpAndSettle();
    expect(find.byType(JobCardScreen), findsOneWidget);
  });

  testWidgets('Save & Next completes the job and opens the next one',
      (tester) async {
    final backend = QueueBackend();
    await pumpCrew(tester, const CrewHomeScreen(),
        backend: backend, capture: FakeCapture());
    await tester.tap(find.text('MH12AB1234'));
    await tester.pumpAndSettle();
    await tester.tap(find.text(CrewText.startJob));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Item a'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Item b'));
    await tester.pumpAndSettle();
    await tester.tap(find.text(CrewText.takePhoto));
    await tester.pumpAndSettle();

    expect(find.text('Save & Next'), findsOneWidget);
    await tester.tap(find.text('Save & Next'));
    await tester.pumpAndSettle();

    expect(backend.jobs['j1']!.status, 'Completed');
    expect(find.byType(JobCardScreen), findsOneWidget);
    expect(find.text('MH12CD5678'), findsWidgets);
    expect(find.text(CrewText.startJob), findsOneWidget);
  });

  testWidgets('the last job says Save', (tester) async {
    final backend = QueueBackend();
    backend.jobs['j1']!.status = 'Completed';
    await pumpCrew(tester, const CrewHomeScreen(), backend: backend);
    await tester.tap(find.text('MH12CD5678'));
    await tester.pumpAndSettle();
    await tester.tap(find.text(CrewText.startJob));
    await tester.pumpAndSettle();
    expect(find.text('Save'), findsOneWidget);
    expect(find.text('Save & Next'), findsNothing);
  });
}
