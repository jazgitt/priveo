// The projected calendar day card (CAL-05 to CAL-10, SCHED-02) and the Home
// schedule items (HOME-01, HOME-04, HOME-08, HOME-09). Data comes from fakes.
import 'package:flutter/material.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/changes_money/data/money_models.dart';
import 'package:priveo/features/changes_money/data/money_repository.dart';
import 'package:priveo/features/customer/calendar/calendar_actions.dart';
import 'package:priveo/features/customer/calendar/calendar_screen.dart';
import 'package:priveo/features/customer/calendar/day_card.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/customer/home/customer_home_data.dart';
import 'package:priveo/features/customer/home/customer_shell.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';
import 'package:priveo/features/support/data/support_models.dart';
import 'package:priveo/features/support/data/support_repository.dart';
import 'package:priveo/features/support/widgets.dart' show linkOpenerProvider;
import 'package:priveo/l10n/app_localizations.dart';

import '../changes_money/fakes.dart' show FakeMoneyRepository;
import '../support/fakes.dart';
import '../support/support_fakes.dart';
import 'customer_slice_test.dart' show FakeReads;

class _Reads extends FakeReads {
  _Reads(this.visits, {this.next = const []});

  final List<CalendarVisit> visits;
  final List<NextServiceDto> next;

  @override
  Future<CalendarMonthDto> calendar(String month, {String? vehicleId}) async =>
      CalendarMonthDto(
        month: month,
        visits: month == '2026-11' ? visits : const [],
        renewals: [
          CalendarRenewalDto(vehicleId: 'v1', date: DateTime(2026, 11, 13)),
        ],
      );

  @override
  Future<List<NextServiceDto>> nextServices() async => next;
}

class _Actions implements CalendarActions {
  final calls = <String>[];

  @override
  Future<String> skip(String vehicleId, DateTime date) async {
    calls.add('skip ${date.day}');
    return 's-1';
  }

  @override
  Future<void> unskip(String vehicleId, String skipId) async =>
      calls.add('unskip $skipId');

  @override
  Future<CutoffChangeResult> changeCutoff(
    String vehicleId,
    DateTime date,
    String cutoff,
  ) async {
    calls.add('cutoff ${date.day} $cutoff');
    return const CutoffChangeResult(status: 'Applied');
  }

  @override
  Future<PreferencesResult> updatePreferences(
    String vehicleId, {
    String? cutoffTime,
    String? interiorDay,
  }) async => PreferencesResult(
    cutoffTime: cutoffTime,
    interiorDay: interiorDay,
    appliesFrom: DateTime(2026, 11, 12),
    frozenDaysUnchanged: 0,
  );
}

CalendarVisit visit(
  int day, {
  String status = 'Projected',
  String source = 'projected',
  List<String> services = const ['Cleaning-External'],
  String? state,
  bool canChange = true,
  String? skipId,
  bool changeRequested = false,
  String? requestedCutoff,
  DateTime? coveredOn,
  DateTime? rescheduledOn,
  String? crew,
}) => CalendarVisit(
  visitId: source == 'visit' ? 'v-$day' : null,
  vehicleId: 'v1',
  date: DateTime(2026, 11, day),
  status: status,
  services: services,
  source: source,
  state: state,
  cutoffTime: '07:00',
  canChange: canChange,
  skipId: skipId,
  changeRequested: changeRequested,
  requestedCutoffTime: requestedCutoff,
  coveredOn: coveredOn,
  rescheduledOn: rescheduledOn,
  crewName: crew,
  startTime: crew == null ? null : '07:00',
  endTime: crew == null ? null : '07:20',
);

Future<void> pumpWith(
  WidgetTester tester,
  Widget body, {
  required CustomerReadsRepository reads,
  CalendarActions? actions,
  List<String>? opened,
  FakeSupportRepository? support,
  DateTime? now,
  String? selectVehicle,
  FakeMoneyRepository? money,
}) async {
  tester.view.physicalSize = const Size(800, 2600);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final container = ProviderContainer(
    overrides: [
      readRefreshProvider.overrideWith((ref) => const Stream<int>.empty()),
      apiProvider.overrideWithValue(FakePriveoApi()),
      customerReadsProvider.overrideWithValue(reads),
      if (money != null) moneyRepositoryProvider.overrideWithValue(money),
      calendarActionsProvider.overrideWithValue(actions ?? _Actions()),
      supportRepositoryProvider.overrideWithValue(
        support ?? FakeSupportRepository(),
      ),
      linkOpenerProvider.overrideWithValue((uri) async {
        opened?.add(uri.toString());
        return true;
      }),
      if (now != null) homeNowProvider.overrideWithValue(() => now),
      sessionStoreProvider.overrideWithValue(
        MemorySessionStore()..write(customerSession),
      ),
      authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
    ],
  );
  addTearDown(container.dispose);
  if (selectVehicle != null) {
    container.read(selectedVehicleProvider.notifier).select(selectVehicle);
  }
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        theme: customerTheme,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(body: body),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Widget calendar() => CalendarScreen(today: DateTime(2026, 11, 10));

void main() {
  group('day card', () {
    testWidgets('a projected day is expected and can be skipped', (
      tester,
    ) async {
      final actions = _Actions();
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([visit(12)]),
        actions: actions,
      );
      await tester.tap(find.bySemanticsLabel('12-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('Expected'), findsWidgets);
      expect(
        find.text('Expected visit. It is confirmed when the week is planned.'),
        findsOneWidget,
      );
      await tester.tap(find.text('Skip this date'));
      await tester.pumpAndSettle();
      expect(actions.calls, ['skip 12']);
    });

    testWidgets('change cutoff time picks a time and sends it', (tester) async {
      final actions = _Actions();
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([visit(12)]),
        actions: actions,
      );
      await tester.tap(find.bySemanticsLabel('12-Nov-26'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Change cutoff time'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('7:30 AM'));
      await tester.pumpAndSettle();
      expect(actions.calls, ['cutoff 12 07:30']);
    });

    testWidgets('a skipped day with a skip can be undone', (tester) async {
      final actions = _Actions();
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([visit(12, status: 'Skipped', skipId: 's-9')]),
        actions: actions,
      );
      await tester.tap(find.bySemanticsLabel('12-Nov-26'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Undo skip'));
      await tester.pumpAndSettle();
      expect(actions.calls, ['unskip s-9']);
    });

    testWidgets('after the cutoff the controls close and Call support opens '
        'the helpline', (tester) async {
      final opened = <String>[];
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([visit(11, canChange: false, status: 'Scheduled')]),
        opened: opened,
      );
      await tester.tap(find.bySemanticsLabel('11-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('Skip this date'), findsNothing);
      expect(
        find.textContaining('The cutoff for this date has passed'),
        findsOneWidget,
      );
      await tester.tap(find.text('Call support'));
      await tester.pumpAndSettle();
      expect(opened, ['tel:+911234567890']);
    });

    testWidgets('a requested change keeps the value and says it is waiting', (
      tester,
    ) async {
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([
          visit(
            12,
            status: 'Scheduled',
            source: 'visit',
            state: 'Change requested',
            changeRequested: true,
            requestedCutoff: '09:00',
          ),
        ]),
      );
      await tester.tap(find.bySemanticsLabel('12-Nov-26'));
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Change requested, awaiting Priveo'),
        findsOneWidget,
      );
      expect(find.textContaining('9:00 AM'), findsOneWidget);
    });

    testWidgets('missed days say where the work was covered or rescheduled', (
      tester,
    ) async {
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([
          visit(
            4,
            status: 'Missed',
            source: 'visit',
            state: 'Covered',
            coveredOn: DateTime(2026, 11, 5),
            canChange: false,
          ),
          visit(
            6,
            status: 'Missed',
            source: 'visit',
            state: 'Rescheduled',
            rescheduledOn: DateTime(2026, 11, 8),
            canChange: false,
          ),
        ]),
      );
      await tester.tap(find.bySemanticsLabel('04-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('Missed. Covered on 05-Nov-26'), findsOneWidget);
      await tester.tap(find.bySemanticsLabel('06-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('Missed. Rescheduled on 08-Nov-26'), findsOneWidget);
    });

    testWidgets('an assigned visit shows the crew member and time', (
      tester,
    ) async {
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([
          visit(12, status: 'Scheduled', source: 'visit', crew: 'Ravi Kumar'),
        ]),
      );
      await tester.tap(find.bySemanticsLabel('12-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('Ravi Kumar, 7:00 AM to 7:20 AM'), findsOneWidget);
    });

    testWidgets('a paused day and the renewal date are shown', (tester) async {
      await pumpWith(
        tester,
        calendar(),
        reads: _Reads([visit(13, status: 'Paused', canChange: false)]),
      );
      await tester.tap(find.bySemanticsLabel('13-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('Your service is paused on this date.'), findsOneWidget);
      expect(find.text('Your plan renews on 13-Nov-26.'), findsOneWidget);
    });

    test('markers: upcoming interior and spa days are outlined shapes', () {
      DayMarker? m(List<String> s, {String status = 'Scheduled'}) =>
          dayMarkerFor([
            visit(12, status: status, source: 'visit', services: s),
          ]);
      expect(
        m(['Cleaning-External', 'Cleaning-Internal']),
        DayMarker.scheduledInterior,
      );
      expect(m(['Deep Spa']), DayMarker.scheduledSpa);
      expect(m(['Cleaning-External']), DayMarker.scheduled);
      expect(dayMarkerFor([visit(12)]), DayMarker.expected);
      expect(dayMarkerFor([visit(12, status: 'Paused')]), DayMarker.paused);
    });
  });

  group('billing cycle', () {
    testWidgets('days outside the plan cycle are greyed out and cannot be selected',
        (tester) async {
      // Cycle 11-Nov-26 to 10-Dec-26. Today (10-Nov) is before it.
      final money = FakeMoneyRepository()
        ..sub = SubscriptionDto(
          vehicleId: 'v1',
          planName: 'Premium Care',
          vehicle: 'Hyundai Creta',
          registration: 'HR 26 DK 8337',
          society: 'DLF Meadows',
          status: 'Active',
          monthlyPriceRupees: 1299,
          paymentMethod: 'UPI',
          cutoffTime: '07:00',
          interiorDay: 'Friday',
          cycleStart: DateTime(2026, 11, 11),
          renewalDate: DateTime(2026, 12, 11),
          cycleDays: 30,
          daysLeft: 30,
          latestPayment: null,
          canPayNext: false,
        );
      await pumpWith(tester, calendar(), reads: _Reads(const []), money: money);
      expect(find.text('Plan duration: 11-Nov-26 to 10-Dec-26 · Active'), findsOneWidget);
      // The selected day (today) is outside the cycle, so no day card shows.
      expect(find.byType(DayCard), findsNothing);
      // A day outside the cycle cannot be selected.
      await tester.tap(find.text('5'), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(find.byType(DayCard), findsNothing);
      // A day inside it can.
      await tester.tap(find.text('15'));
      await tester.pumpAndSettle();
      expect(find.byType(DayCard), findsOneWidget);
    });
  });

  group('home', () {
    final tomorrow = NextServiceDto(
      vehicleId: 'v2',
      visitId: 'v-9',
      date: DateTime(2026, 11, 11),
      service: 'Cleaning-External',
      status: 'Scheduled',
      services: const ['Cleaning-External'],
      cutoffTime: '06:30',
      crewName: 'Ravi Kumar',
      startTime: '06:40',
      endTime: '07:00',
    );
    final now = DateTime(2026, 11, 10, 9, 0);

    testWidgets('greets by time of day and shows Tomorrow with the crew', (
      tester,
    ) async {
      await pumpWith(
        tester,
        CustomerHomeScreen(onCalendar: () {}),
        reads: _Reads(const [], next: [tomorrow]),
        now: now,
        selectVehicle: 'v2',
      );
      expect(find.text('Good morning,'), findsOneWidget);
      expect(find.text('Tomorrow, Wed 11-Nov-26'), findsOneWidget);
      expect(find.text('Ravi Kumar, 6:40 AM to 7:00 AM'), findsOneWidget);
    });

    testWidgets('the evening greeting', (tester) async {
      await pumpWith(
        tester,
        CustomerHomeScreen(onCalendar: () {}),
        reads: _Reads(const []),
        now: DateTime(2026, 11, 10, 19, 0),
      );
      expect(find.text('Good evening,'), findsOneWidget);
    });

    testWidgets('a due check-in shows a Monthly check-in card', (tester) async {
      final support = FakeSupportRepository()
        ..pending = const [
          PendingCheckIn(
            subscriptionId: 's1',
            vehicleLabel: 'Check-in car',
            cycleStart: '2026-10-14',
          ),
        ];
      await pumpWith(
        tester,
        CustomerHomeScreen(onCalendar: () {}),
        reads: _Reads(const []),
        support: support,
        now: now,
      );
      expect(find.text('Monthly check-in'), findsOneWidget);
      expect(find.text('Check-in car'), findsOneWidget);
    });

    testWidgets('no check-in card when nothing is due', (tester) async {
      await pumpWith(
        tester,
        CustomerHomeScreen(onCalendar: () {}),
        reads: _Reads(const []),
        now: now,
      );
      expect(find.text('Monthly check-in'), findsNothing);
    });

    testWidgets('the Add-ons card is only for an Active vehicle', (
      tester,
    ) async {
      await pumpWith(
        tester,
        CustomerHomeScreen(onCalendar: () {}),
        reads: _Reads(const []),
        now: now,
      );
      expect(find.text('Deep Spa'), findsOneWidget);
    });

    testWidgets('standalone Spa is offered without a subscription', (
      tester,
    ) async {
      await pumpWith(
        tester,
        CustomerHomeScreen(onCalendar: () {}),
        reads: _Reads(const []),
        now: now,
        selectVehicle: 'v3',
      );
      expect(find.text('Deep Spa'), findsOneWidget);
    });
  });
}
