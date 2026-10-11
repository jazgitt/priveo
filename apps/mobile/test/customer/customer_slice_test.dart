// The customer slice: calendar (CAL-), service details with proof (SVC-),
// history, vehicles (VEH-), account, notifications (NOTIF-) and the next
// service card on Home (HOME-04). The data comes from a fake repository.
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/auth/auth_controller.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/customer/account/account_screen.dart';
import 'package:priveo/features/customer/calendar/calendar_screen.dart';
import 'package:priveo/features/support/data/support_repository.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/customer/data/proof_reads_repository.dart';
import 'package:priveo/features/customer/home/todays_clean_strip.dart';
import 'package:priveo/features/customer/history/history_screen.dart';
import 'package:priveo/features/customer/home/customer_home_data.dart';
import 'package:priveo/features/customer/home/customer_shell.dart';
import 'package:priveo/features/customer/notifications/notifications_screen.dart';
import 'package:priveo/features/customer/routes.dart' as customer;
import 'package:priveo/features/customer/vehicles/vehicles_screen.dart';
import 'package:priveo/features/customer/visit/visit_details_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';

import '../support/fakes.dart';
import '../support/support_fakes.dart';

class FakeReads implements CustomerReadsRepository {
  FakeReads({this.failCalendar = false});

  bool failCalendar;
  final markedRead = <String>[];
  var markedAll = false;
  var unread = true;

  static final visits = [
    CalendarVisit(
      visitId: 'v-1',
      vehicleId: 'v1',
      date: DateTime(2026, 11, 2),
      status: 'Completed',
      services: ['Cleaning-External', 'Cleaning-Internal'],
    ),
    CalendarVisit(
      visitId: 'v-2',
      vehicleId: 'v1',
      date: DateTime(2026, 11, 3),
      status: 'Skipped',
      services: ['Cleaning-External'],
    ),
    CalendarVisit(
      visitId: 'v-3',
      vehicleId: 'v1',
      date: DateTime(2026, 11, 10),
      status: 'Scheduled',
      services: ['Cleaning-External'],
    ),
  ];

  @override
  Future<CalendarMonthDto> calendar(String month, {String? vehicleId}) async {
    if (failCalendar) {
      throw const ApiFailure(code: 'x', message: 'Calendar is down.');
    }
    return CalendarMonthDto(
      month: month,
      visits: month == '2026-11' ? visits : const [],
    );
  }

  @override
  Future<List<NextServiceDto>> nextServices() async => [
    NextServiceDto(
      vehicleId: 'v2',
      visitId: 'v-9',
      date: DateTime(2026, 11, 12),
      service: 'Cleaning-External',
      status: 'Scheduled',
    ),
  ];

  static VisitDetailDto richVisit({int? rating}) => VisitDetailDto(
    id: 'v-proof',
    vehicleId: 'v1',
    vehicleRegistration: 'MH 12 AB 1234',
    vehicleModel: 'Hyundai Creta',
    date: DateTime(2026, 11, 2),
    status: 'Completed',
    finishedAt: DateTime(2026, 11, 2, 7, 30),
    rating: rating,
    jobs: [
      JobDto(
        id: 'j-1',
        service: 'Cleaning-External',
        status: 'Done',
        crewName: 'Ravi',
        crewSociety: 'Green Meadows',
        finishedAt: DateTime(2026, 11, 2, 7, 30),
        checklist: [
          ChecklistItemDto(
            key: 'body',
            label: 'Exterior body cleaned',
            checkedAt: DateTime(2026, 11, 2, 7, 10),
          ),
          ChecklistItemDto(
            key: 'glass',
            label: 'Glass cleaned',
            checkedAt: DateTime(2026, 11, 2, 7, 15),
          ),
          const ChecklistItemDto(key: 'wheels', label: 'Wheels cleaned'),
        ],
        proof: [
          ProofDto(
            kind: 'photo',
            url: 'https://media.test/a.jpg',
            stage: 'Before',
            takenAt: DateTime(2026, 11, 2, 7, 0),
          ),
          ProofDto(
            kind: 'photo',
            url: 'https://media.test/b.jpg',
            stage: 'After',
            takenAt: DateTime(2026, 11, 2, 7, 25),
          ),
          const ProofDto(
            kind: 'video',
            url: 'https://media.test/c.mp4',
            stage: 'During',
          ),
        ],
      ),
    ],
  );

  int? rated;

  @override
  Future<VisitDetailDto> visit(String visitId) async => visitId == 'v-proof'
      ? richVisit(rating: rated)
      : VisitDetailDto(
    id: visitId,
    vehicleId: 'v1',
    vehicleRegistration: 'MH 12 AB 1234',
    vehicleModel: 'Hyundai Creta',
    date: DateTime(2026, 11, 2),
    status: 'Completed',
    jobs: const [
      JobDto(
        id: 'j-1',
        service: 'Cleaning-External',
        status: 'Done',
        proof: [
          ProofDto(kind: 'photo', url: 'https://media.test/a.jpg'),
          ProofDto(kind: 'photo', url: 'https://media.test/b.jpg'),
          ProofDto(kind: 'video', url: 'https://media.test/c.mp4'),
        ],
      ),
      JobDto(
        id: 'j-2',
        service: 'Cleaning-Internal',
        status: 'Done',
        proof: [],
      ),
    ],
  );

  @override
  Future<List<HistoryItemDto>> history({
    String? vehicleId,
    int offset = 0,
  }) async => [
    HistoryItemDto(
      visitId: 'v-2',
      vehicleId: 'v1',
      date: DateTime(2026, 11, 3),
      status: 'Skipped',
      services: ['Cleaning-External'],
      photoCount: 0,
    ),
    HistoryItemDto(
      visitId: 'v-1',
      vehicleId: 'v1',
      date: DateTime(2026, 11, 2),
      status: 'Completed',
      services: ['Cleaning-External', 'Cleaning-Internal'],
      photoCount: 2,
    ),
  ];

  @override
  Future<List<VehicleSummaryDto>> vehicles() async => const [
    VehicleSummaryDto(
      id: 'v1',
      registration: 'MH 12 AB 1234',
      model: 'Creta',
      society: 'Green Meadows',
      subscriptionStatus: 'Active',
    ),
    VehicleSummaryDto(
      id: 'v3',
      registration: '',
      model: 'Punch',
      society: 'Green Meadows',
      subscriptionStatus: null,
    ),
  ];

  @override
  Future<VehicleDetailDto> vehicle(String vehicleId) async =>
      const VehicleDetailDto(
        id: 'v1',
        registration: 'MH 12 AB 1234',
        model: 'Creta',
        society: 'Green Meadows',
        subscriptionStatus: 'Active',
        make: 'Hyundai',
        variant: 'SX',
        category: 'SUV',
        parking: 'B2-14',
        monthlyPriceRupees: 1299,
        cutoffTime: '07:00',
        interiorDay: null,
      );

  @override
  Future<InboxDto> inbox() async => InboxDto(
    unreadCount: unread ? 1 : 0,
    items: [
      NotificationDto(
        id: 'n-1',
        event: 'service_completed',
        title: "Today's clean is done",
        body: '5 of 5 checks',
        visitId: 'v-1',
        createdAt: DateTime(2026, 11, 2, 8, 30),
        read: !unread,
      ),
    ],
  );

  @override
  Future<void> markRead(String notificationId) async {
    markedRead.add(notificationId);
    unread = false;
  }

  @override
  Future<void> markAllRead() async {
    markedAll = true;
    unread = false;
  }

  @override
  Future<void> registerDevice(String token, String platform) async {}
}

class FakeProofReads implements ProofReadsRepository {
  FakeProofReads({this.cleans = const []});

  List<TodayCleanDto> cleans;

  @override
  Future<List<HistoryItemDto>> historyMonth(
    String month, {
    String? vehicleId,
    int offset = 0,
  }) async => [
    HistoryItemDto(
      visitId: 'v-2',
      vehicleId: 'v1',
      date: DateTime(2026, 11, 3),
      status: 'Skipped',
      services: ['Cleaning-External'],
      photoCount: 0,
    ),
    HistoryItemDto(
      visitId: 'v-1',
      vehicleId: 'v1',
      date: DateTime(2026, 11, 2),
      status: 'Completed',
      services: ['Cleaning-External', 'Cleaning-Internal'],
      photoCount: 2,
      finishedAt: DateTime(2026, 11, 2, 7, 30),
      rating: 4,
    ),
  ];

  @override
  Future<HistoryMetaDto> historyMeta({String? vehicleId}) async =>
      HistoryMetaDto(
        memberSince: DateTime(2026, 9, 14),
        latestMonth: '2026-11',
        earliestMonth: '2026-09',
      );

  @override
  Future<List<TodayCleanDto>> today() async => cleans;
}

Future<ProviderContainer> pumpScreen(
  WidgetTester tester,
  Widget screen, {
  FakeReads? reads,
  FakeProofReads? proof,
  FakeAuthRepository? auth,
  MemorySessionStore? store,
  bool scaffold = false,
}) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final container = ProviderContainer(
    overrides: [
      proofReadsProvider.overrideWithValue(proof ?? FakeProofReads()),
      supportRepositoryProvider.overrideWithValue(FakeSupportRepository()),
      apiProvider.overrideWithValue(FakePriveoApi()),
      customerReadsProvider.overrideWithValue(reads ?? FakeReads()),
      sessionStoreProvider.overrideWithValue(
        store ?? (MemorySessionStore()..write(customerSession)),
      ),
      authRepositoryProvider.overrideWithValue(auth ?? FakeAuthRepository()),
    ],
  );
  addTearDown(container.dispose);
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
        home: scaffold ? Scaffold(body: screen) : screen,
      ),
    ),
  );
  await tester.pumpAndSettle();
  return container;
}

void main() {
  group('calendar', () {
    testWidgets('shows the month, markers and the day card of today', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        CalendarScreen(today: DateTime(2026, 11, 10)),
        scaffold: true,
      );
      expect(find.text('November 2026'), findsOneWidget);
      expect(find.text('Mon'), findsOneWidget);
      // Today's card: a scheduled visit with its cutoff time.
      expect(find.text('10-Nov-26'), findsOneWidget);
      expect(
        find.text(
          'Scheduled to be completed by 7:00 AM. Proof appears after the visit.',
        ),
        findsOneWidget,
      );
      // Markers: the legend lists all six.
      expect(find.text('Completed'), findsOneWidget);
      expect(find.text('Exterior + Interior'), findsOneWidget);
      expect(find.text('Missed'), findsOneWidget);
    });

    testWidgets('a completed day opens the service details', (tester) async {
      await pumpScreen(
        tester,
        CalendarScreen(today: DateTime(2026, 11, 10)),
        scaffold: true,
      );
      await tester.tap(find.bySemanticsLabel('02-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('View service details'), findsOneWidget);
      await tester.tap(find.text('View service details'));
      await tester.pumpAndSettle();
      expect(find.text('Service details'), findsOneWidget);
      expect(find.text('Cleaning-Internal'), findsOneWidget);
    });

    testWidgets('a skipped day and a day without a visit say so', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        CalendarScreen(today: DateTime(2026, 11, 10)),
        scaffold: true,
      );
      await tester.tap(find.bySemanticsLabel('03-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('You skipped this date.'), findsOneWidget);
      await tester.tap(find.bySemanticsLabel('04-Nov-26'));
      await tester.pumpAndSettle();
      expect(find.text('No visit on this day.'), findsOneWidget);
    });

    testWidgets('the arrows move between months', (tester) async {
      await pumpScreen(
        tester,
        CalendarScreen(today: DateTime(2026, 11, 10)),
        scaffold: true,
      );
      await tester.tap(find.byTooltip('Next month'));
      await tester.pumpAndSettle();
      expect(find.text('December 2026'), findsOneWidget);
      await tester.tap(find.byTooltip('Previous month'));
      await tester.tap(find.byTooltip('Previous month'));
      await tester.pumpAndSettle();
      expect(find.text('October 2026'), findsOneWidget);
    });

    testWidgets('a failed load can be retried', (tester) async {
      final reads = FakeReads(failCalendar: true);
      await pumpScreen(
        tester,
        CalendarScreen(today: DateTime(2026, 11, 10)),
        reads: reads,
        scaffold: true,
      );
      expect(find.text('Calendar is down.'), findsOneWidget);
      reads.failCalendar = false;
      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();
      expect(find.text('November 2026'), findsOneWidget);
    });
  });

  group('service details', () {
    testWidgets('lists the jobs and the photos, and opens the viewer', (
      tester,
    ) async {
      await pumpScreen(tester, const VisitDetailsScreen(visitId: 'v-1'));
      expect(find.text('02-Nov-26'), findsOneWidget);
      expect(find.text('Completed'), findsOneWidget);
      expect(find.text('Cleaning-External'), findsOneWidget);
      expect(find.text('Play video'), findsOneWidget);
      expect(find.byType(Image), findsNWidgets(2));
      await tester.tap(find.byType(Image).first);
      await tester.pumpAndSettle();
      expect(find.text('1 / 2'), findsOneWidget);
      await tester.tap(find.byTooltip('Close'));
      await tester.pumpAndSettle();
      expect(find.text('Service details'), findsOneWidget);
    });
  });

  group('history', () {
    testWidgets('lists visits and opens a completed one', (tester) async {
      await pumpScreen(tester, const HistoryScreen());
      expect(find.text('03-Nov-26'), findsOneWidget);
      expect(find.text('Skipped'), findsOneWidget);
      expect(find.textContaining('2 photos'), findsOneWidget);
      // Finish time and the rating given (HIST-01), and the footer (HIST-02).
      expect(find.text('02-Nov-26  ·  7:30 AM'), findsOneWidget);
      expect(find.text('4 stars'), findsOneWidget);
      expect(find.textContaining('Member since 14-Sep-26'), findsOneWidget);
      await tester.tap(find.text('02-Nov-26  ·  7:30 AM'));
      await tester.pumpAndSettle();
      expect(find.text('Service details'), findsOneWidget);
    });
  });

  group('proof on service details', () {
    testWidgets('shows the crew card, checklist and AFTER label', (
      tester,
    ) async {
      await pumpScreen(tester, const VisitDetailsScreen(visitId: 'v-proof'));
      expect(find.text('Finished at 7:30 AM'), findsOneWidget);
      expect(find.text('Ravi'), findsOneWidget);
      expect(find.text('Priveo crew · Green Meadows'), findsOneWidget);
      expect(find.text('2 of 3 done'), findsOneWidget);
      expect(find.text('Exterior body cleaned'), findsOneWidget);
      expect(find.text('AFTER'), findsOneWidget);
      expect(find.text('Report an issue with this clean'), findsOneWidget);
      // The viewer caption names the stage, time and service.
      await tester.tap(find.byType(Image).last);
      await tester.pumpAndSettle();
      expect(find.text('After · 7:25 AM · Cleaning-External'), findsOneWidget);
    });

    testWidgets('offers a rating', (tester) async {
      await pumpScreen(tester, const VisitDetailsScreen(visitId: 'v-proof'));
      expect(find.text('Rate this clean'), findsNWidgets(2));
    });

    testWidgets('shows the rating given', (tester) async {
      final reads = FakeReads()..rated = 5;
      await pumpScreen(
        tester,
        const VisitDetailsScreen(visitId: 'v-proof'),
        reads: reads,
      );
      expect(find.text('You rated this clean 5 of 5'), findsOneWidget);
      expect(find.text('Change rating'), findsOneWidget);
    });

    testWidgets('opens the report form linked to the visit', (tester) async {
      await pumpScreen(tester, const VisitDetailsScreen(visitId: 'v-proof'));
      await tester.ensureVisible(find.text('Report an issue with this clean'));
      await tester.tap(find.text('Report an issue with this clean'));
      await tester.pumpAndSettle();
      expect(find.text('Report an issue'), findsWidgets);
    });
  });

  group('today strip', () {
    final clean = TodayCleanDto(
      vehicleId: 'v1',
      visitId: 'v-proof',
      finishedAt: DateTime(2026, 11, 2, 7, 30),
      checksDone: 5,
      checksTotal: 5,
      photoCount: 3,
    );

    testWidgets('shows the summary and opens the proof', (tester) async {
      await pumpScreen(
        tester,
        const TodaysCleanStrip(),
        proof: FakeProofReads(cleans: [clean]),
        scaffold: true,
      );
      expect(find.text("Today's clean is done"), findsOneWidget);
      expect(
        find.text('Finished at 7:30 AM · 5 of 5 checks · 3 photos'),
        findsOneWidget,
      );
      expect(find.text("Rate today's clean"), findsOneWidget);
      await tester.tap(find.text('View proof'));
      await tester.pumpAndSettle();
      expect(find.text('Service details'), findsOneWidget);
    });

    testWidgets('shows nothing when no clean finished today', (tester) async {
      await pumpScreen(tester, const TodaysCleanStrip(), scaffold: true);
      expect(find.text("Today's clean is done"), findsNothing);
    });
  });

  group('vehicles', () {
    testWidgets('lists vehicles and opens a vehicle', (tester) async {
      await pumpScreen(tester, const VehiclesScreen());
      expect(find.text('MH 12 AB 1234'), findsOneWidget);
      expect(find.text('Number to be added'), findsOneWidget);
      expect(find.text('No subscription'), findsOneWidget);
      await tester.tap(find.text('MH 12 AB 1234'));
      await tester.pumpAndSettle();
      expect(find.text('Hyundai Creta'), findsOneWidget);
      expect(find.text('B2-14'), findsOneWidget);
      expect(find.text('₹1,299 a month'), findsOneWidget);
      expect(find.text('7:00 AM'), findsOneWidget);
      // A field with no value is said plainly.
      expect(find.text('Not on file'), findsOneWidget);
    });
  });

  group('account', () {
    testWidgets('shows the name, the unread count and signs out', (
      tester,
    ) async {
      final auth = FakeAuthRepository();
      final container = await pumpScreen(
        tester,
        const AccountScreen(),
        auth: auth,
        scaffold: true,
      );
      expect(find.text('My account'), findsOneWidget);
      // The session is read from the store, so wait for it.
      await container.read(authControllerProvider.future);
      await tester.pumpAndSettle();
      expect(find.text('Aarav Mehta'), findsOneWidget);
      expect(find.text('1'), findsOneWidget);
      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();
      expect(auth.logoutCalls, 1);
    });

    testWidgets('opens the vehicles list and the notifications', (
      tester,
    ) async {
      await pumpScreen(tester, const AccountScreen(), scaffold: true);
      await tester.tap(find.text('Notifications'));
      await tester.pumpAndSettle();
      expect(find.text("Today's clean is done"), findsOneWidget);
    });
  });

  group('notifications', () {
    testWidgets('a tap marks the message read and opens its visit', (
      tester,
    ) async {
      final reads = FakeReads();
      await pumpScreen(tester, const NotificationsScreen(), reads: reads);
      expect(find.text('Mark all as read'), findsOneWidget);
      await tester.tap(find.text("Today's clean is done"));
      await tester.pumpAndSettle();
      expect(reads.markedRead, ['n-1']);
      expect(find.text('Service details'), findsOneWidget);
    });

    testWidgets('mark all as read', (tester) async {
      final reads = FakeReads();
      await pumpScreen(tester, const NotificationsScreen(), reads: reads);
      await tester.tap(find.text('Mark all as read'));
      await tester.pumpAndSettle();
      expect(reads.markedAll, isTrue);
      expect(find.text('Mark all as read'), findsNothing);
    });
  });

  group('home next service', () {
    testWidgets('fills the card from the visits when Home has none', (
      tester,
    ) async {
      final reads = FakeReads();
      final container = ProviderContainer(
        overrides: [
          apiProvider.overrideWithValue(FakePriveoApi()),
          customerReadsProvider.overrideWithValue(reads),
          sessionStoreProvider.overrideWithValue(
            MemorySessionStore()..write(customerSession),
          ),
          authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
        ],
      );
      addTearDown(container.dispose);
      container.read(selectedVehicleProvider.notifier).select('v2');
      tester.view.physicalSize = const Size(800, 2400);
      tester.view.devicePixelRatio = 2;
      addTearDown(tester.view.reset);
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
            home: Scaffold(body: CustomerHomeScreen(onCalendar: () {})),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('12-Nov-26'), findsOneWidget);
      expect(find.text('Not scheduled yet'), findsNothing);
    });
  });

  test('routes list the slice pages', () {
    expect(customer.routes.map((r) => r.path), [
      'visit/:id',
      'history',
      'vehicles',
      'vehicles/:id',
      'notifications',
    ]);
  });
}
