// The admin quick actions: home on real data, complaints, feedback and the
// read-only scheduling views (MQ-1, MQ-2, MQ-7).
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/admin_quick/admin_quick_strings.dart';
import 'package:priveo/features/admin_quick/data/admin_quick_models.dart';
import 'package:priveo/features/admin_quick/data/admin_quick_repository.dart';
import 'package:priveo/features/admin_quick/home/admin_home_screen.dart';
import 'package:priveo/features/admin_quick/routes.dart' as quick;
import 'package:priveo/l10n/app_localizations.dart';

class FakeAdminQuickRepository implements AdminQuickRepository {
  QuickHome homeValue = const QuickHome(
    alertCount: 3,
    needsSchedulingCount: 2,
    openComplaintsCount: 1,
    paymentsToConfirmCount: 1,
    paymentsToConfirm: [
      QuickPayment(
        id: 'p1',
        customerLabel: 'Asha Rao, Flat A-101',
        amountRupees: 1299,
        reference: 'Plan, October',
      ),
    ],
    societies: [SocietyRef(id: 's1', name: 'DLF Meadows')],
  );

  List<QuickComplaint> complaintRows = [
    QuickComplaint(
      id: 'c1',
      displayId: '#C-0001',
      category: 'Cleaning quality',
      description: 'Streaks on the glass',
      status: 'Raised',
      createdAt: DateTime.utc(2026, 10, 10, 6),
      customerName: 'Asha Rao',
      society: 'DLF Meadows',
      flat: 'A-101',
      overdue: true,
    ),
    QuickComplaint(
      id: 'c2',
      displayId: '#C-0002',
      category: 'Billing',
      description: 'Charged twice',
      status: 'Resolved',
      createdAt: DateTime.utc(2026, 10, 9, 6),
      customerName: 'Ben Roy',
      society: 'DLF Meadows',
      flat: 'B-2',
      overdue: false,
    ),
  ];

  final statusCalls = <List<String>>[];
  final noteCalls = <List<String>>[];
  final complaintFilters = <String?>[];
  final feedbackFilters = <int?>[];
  bool failNext = false;

  void _maybeFail() {
    if (failNext) {
      failNext = false;
      throw const ApiFailure(
        code: 'x',
        message: 'Could not save that.',
        statusCode: 400,
      );
    }
  }

  @override
  Future<QuickHome> home() async => homeValue;

  @override
  Future<List<QuickComplaint>> complaints({
    String? status,
    String? category,
  }) async {
    complaintFilters.add(status);
    return [
      for (final c in complaintRows)
        if (status == null || c.status == status) c,
    ];
  }

  @override
  Future<QuickComplaint> complaint(String id) async =>
      complaintRows.firstWhere((c) => c.id == id);

  QuickComplaint _replace(String id, String status, String note) {
    final old = complaintRows.firstWhere((c) => c.id == id);
    final next = QuickComplaint(
      id: old.id,
      displayId: old.displayId,
      category: old.category,
      description: old.description,
      status: status,
      createdAt: old.createdAt,
      customerName: old.customerName,
      society: old.society,
      flat: old.flat,
      overdue: old.overdue,
      updates: [
        ...old.updates,
        ThreadUpdate(
          authorRole: 'admin',
          note: note,
          status: status == old.status ? null : status,
          createdAt: DateTime.utc(2026, 10, 11, 8),
        ),
      ],
    );
    complaintRows = [for (final c in complaintRows) c.id == id ? next : c];
    return next;
  }

  @override
  Future<QuickComplaint> setStatus(
    String id,
    String status,
    String note,
  ) async {
    _maybeFail();
    statusCalls.add([id, status, note]);
    return _replace(id, status, note);
  }

  @override
  Future<QuickComplaint> addNote(String id, String note) async {
    _maybeFail();
    noteCalls.add([id, note]);
    final c = complaintRows.firstWhere((c) => c.id == id);
    return _replace(id, c.status, note);
  }

  @override
  Future<List<QuickFeedback>> feedback({int? rating}) async {
    feedbackFilters.add(rating);
    final all = [
      QuickFeedback(
        id: 'f1',
        category: 'Glass',
        rating: 2,
        comment: 'Smudges again',
        customerName: 'Asha Rao',
        society: 'DLF Meadows',
        createdAt: DateTime.utc(2026, 10, 10),
      ),
      QuickFeedback(
        id: 'f2',
        category: null,
        rating: 5,
        comment: 'Lovely',
        customerName: 'Ben Roy',
        society: 'DLF Meadows',
        createdAt: DateTime.utc(2026, 10, 10),
      ),
    ];
    return [
      for (final f in all)
        if (rating == null || f.rating == rating) f,
    ];
  }

  @override
  Future<QuickRatings> ratings() async =>
      const QuickRatings(count: 8, average: 4.5, tagCounts: {});

  @override
  Future<List<QuickJob>> needsScheduling({String? societyId}) async => [
    QuickJob(
      id: 'j1',
      date: DateTime(2026, 10, 18),
      vehicle: 'Hyundai Creta',
      registration: 'MH12AB0001',
      service: 'Deep Spa',
      status: 'Scheduled',
      reason: 'No crew had room',
    ),
  ];

  DateTime? dayAsked;
  String? daySociety;

  @override
  Future<DaySchedule> day(DateTime date, {String? societyId}) async {
    dayAsked = date;
    daySociety = societyId;
    return DaySchedule(
      date: date,
      scheduleStatus: 'Frozen',
      total: 3,
      done: 1,
      left: 2,
      crew: const [
        DayCrew(
          crewId: 'm1',
          crewName: 'Ravi Kumar',
          jobs: [
            DayJob(
              id: 'a',
              time: '06:00',
              endTime: '06:20',
              vehicle: 'Hyundai Creta',
              registration: 'MH12AB0001',
              service: 'Cleaning-External',
              status: 'Completed',
              late: false,
            ),
            DayJob(
              id: 'b',
              time: '06:20',
              endTime: '06:40',
              vehicle: 'Maruti Swift',
              registration: 'MH12AB0002',
              service: 'Cleaning-External',
              status: 'Scheduled',
              late: true,
            ),
          ],
        ),
        DayCrew(
          crewId: null,
          crewName: 'Not assigned',
          jobs: [
            DayJob(
              id: 'c',
              time: null,
              endTime: null,
              vehicle: 'Tata Punch',
              registration: 'MH12AB0003',
              service: 'Deep Spa',
              status: 'Scheduled',
              late: false,
            ),
          ],
        ),
      ],
    );
  }

  @override
  Future<List<DayCapacity>> capacity(
    String societyId,
    DateTime start, {
    int days = 7,
  }) async => [
    for (var i = 0; i < days; i++)
      DayCapacity(
        date: start.add(Duration(days: i)),
        capacityMinutes: 120,
        demandMinutes: i == 1 ? 200 : 60,
        scheduledMinutes: 60,
        overCapacity: i == 1,
      ),
  ];
}

Future<void> pump(
  WidgetTester tester,
  FakeAdminQuickRepository repo, {
  String initial = '/admin',
}) async {
  tester.view.physicalSize = const Size(800, 2600);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final router = GoRouter(
    initialLocation: initial,
    routes: [
      GoRoute(
        path: '/admin',
        builder: (_, _) =>
            Theme(data: adminTheme, child: const AdminHomeScreen()),
      ),
      ...quick.routes,
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [adminQuickRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp.router(
        theme: adminTheme,
        routerConfig: router,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> tap(WidgetTester tester, Finder f) async {
  await tester.ensureVisible(f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

void main() {
  group('home', () {
    testWidgets('shows real counts and a payment to confirm', (tester) async {
      await pump(tester, FakeAdminQuickRepository());
      expect(find.text('3'), findsOneWidget);
      expect(find.text('Open complaints'), findsOneWidget);
      expect(find.text('Asha Rao, Flat A-101'), findsOneWidget);
      expect(find.text('Plan, October'), findsOneWidget);
    });

    testWidgets('opens every quick action', (tester) async {
      final repo = FakeAdminQuickRepository();
      for (final e in {
        'Complaints': '#C-0001  Cleaning quality',
        'Feedback and ratings': 'Average 4.5 from 8 ratings',
        'Day schedule': '3 jobs, 1 done, 2 left',
        'Capacity': 'Over capacity',
      }.entries) {
        await pump(tester, repo);
        await tap(tester, find.widgetWithText(OutlinedButton, e.key));
        expect(find.textContaining(e.value), findsWidgets, reason: e.key);
      }
      await pump(tester, repo);
      await tap(
        tester,
        find.widgetWithText(OutlinedButton, 'Needs scheduling'),
      );
      expect(find.text('Deep Spa, 18-Oct-26'), findsOneWidget);
    });
  });

  group('complaints', () {
    testWidgets('filters by status', (tester) async {
      final repo = FakeAdminQuickRepository();
      await pump(tester, repo, initial: '/admin/complaints');
      expect(find.textContaining('#C-0001'), findsOneWidget);
      expect(find.textContaining('#C-0002'), findsOneWidget);
      expect(
        find.text('Open for more than 4 hours'),
        findsNothing,
        reason: 'it is part of a longer text',
      );
      await tap(tester, find.widgetWithText(ChoiceChip, 'Resolved'));
      expect(find.textContaining('#C-0001'), findsNothing);
      expect(find.textContaining('#C-0002'), findsOneWidget);
      expect(repo.complaintFilters.last, 'Resolved');
    });

    testWidgets('changes the status with a note', (tester) async {
      final repo = FakeAdminQuickRepository();
      await pump(tester, repo, initial: '/admin/complaints/c1');
      expect(find.text('Streaks on the glass'), findsOneWidget);
      // Save is off until a different status is chosen.
      final save = find.widgetWithText(FilledButton, 'Save status');
      expect(tester.widget<FilledButton>(save).onPressed, isNull);
      await tap(tester, find.widgetWithText(ChoiceChip, 'In progress'));
      await tester.enterText(find.byType(TextField), 'Sent a cleaner');
      await tap(tester, save);
      expect(repo.statusCalls, [
        ['c1', 'In progress', 'Sent a cleaner'],
      ]);
      expect(
        find.text('Sent a cleaner\nStatus: In progress\n11-Oct-26'),
        findsOneWidget,
      );
    });

    testWidgets('adds a note, and asks for text first', (tester) async {
      final repo = FakeAdminQuickRepository();
      await pump(tester, repo, initial: '/admin/complaints/c1');
      await tap(tester, find.widgetWithText(OutlinedButton, 'Add note'));
      expect(find.text('Write a note first.'), findsOneWidget);
      expect(repo.noteCalls, isEmpty);
      await tester.enterText(find.byType(TextField), 'Called the customer');
      await tap(tester, find.widgetWithText(OutlinedButton, 'Add note'));
      expect(repo.noteCalls, [
        ['c1', 'Called the customer'],
      ]);
    });

    testWidgets('shows the server message when a save fails', (tester) async {
      final repo = FakeAdminQuickRepository()..failNext = true;
      await pump(tester, repo, initial: '/admin/complaints/c1');
      await tester.enterText(find.byType(TextField), 'Hello');
      await tap(tester, find.widgetWithText(OutlinedButton, 'Add note'));
      expect(find.text('Could not save that.'), findsOneWidget);
    });
  });

  group('feedback', () {
    testWidgets('shows the average and filters by rating', (tester) async {
      final repo = FakeAdminQuickRepository();
      await pump(tester, repo, initial: '/admin/feedback');
      expect(find.text('Average 4.5 from 8 ratings'), findsOneWidget);
      expect(find.textContaining('Smudges again'), findsOneWidget);
      expect(find.textContaining('Lovely'), findsOneWidget);
      await tap(tester, find.widgetWithText(ChoiceChip, '5 stars'));
      expect(find.textContaining('Smudges again'), findsNothing);
      expect(repo.feedbackFilters.last, 5);
    });
  });

  group('scheduling', () {
    testWidgets('the day groups jobs by crew and moves by a day', (
      tester,
    ) async {
      final repo = FakeAdminQuickRepository();
      await pump(tester, repo, initial: '/admin/day');
      expect(find.text('Ravi Kumar'), findsOneWidget);
      expect(find.text('Not assigned'), findsOneWidget);
      expect(
        find.textContaining('Maruti Swift MH12AB0002, Scheduled, Late'),
        findsOneWidget,
      );
      expect(find.textContaining('No time'), findsOneWidget);
      final before = repo.dayAsked!;
      await tap(tester, find.byTooltip('Next day'));
      expect(repo.dayAsked, before.add(const Duration(days: 1)));
    });

    testWidgets('capacity starts on a Sunday and marks over capacity days', (
      tester,
    ) async {
      final repo = FakeAdminQuickRepository();
      await pump(tester, repo, initial: '/admin/capacity');
      expect(find.text('Over capacity'), findsOneWidget);
      expect(
        find.text('Crew 120 min, work 60 min, placed 60 min'),
        findsWidgets,
      );
    });
  });

  test('the ARB fragment has the same keys and words as the code', () {
    final arb =
        jsonDecode(
              File('lib/l10n/fragments/admin_quick.arb').readAsStringSync(),
            )
            as Map<String, dynamic>;
    final words = {
      for (final e in arb.entries)
        if (!e.key.startsWith('@')) e.key: e.value,
    };
    expect(words, AdminQuickText.all);
  });
}
