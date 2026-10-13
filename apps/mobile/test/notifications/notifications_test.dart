// Notification settings (SET-), tap-through paths (NOTIF-02, CHK-05), the push
// registration after sign-in (NOTIF-01) and the crew inbox (CRW-NOT-).
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/auth_controller.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/common/push/push_registration.dart';
import 'package:priveo/features/crew/notifications/crew_notifications.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/customer/settings/notification_prefs_repository.dart';
import 'package:priveo/features/customer/settings/routes.dart';
import 'package:priveo/features/customer/settings/settings_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';

import '../support/fakes.dart';

class _FakePrefs implements NotificationPrefsRepository {
  final calls = <String>[];
  var items = [
    for (final e in const [
      ('service_completed', 'Service completed'),
      ('service_skipped', 'Service skipped'),
      ('complaint_update', 'Complaint update'),
      ('renewal_reminder', 'Renewal reminder'),
      ('monthly_check_in', 'Monthly check-in'),
    ])
      NotificationPrefDto(
        event: e.$1,
        title: e.$2,
        description: 'About ${e.$2}',
        enabled: true,
      ),
  ];

  @override
  Future<List<NotificationPrefDto>> load() async => items;

  @override
  Future<List<NotificationPrefDto>> set(String event, bool enabled) async {
    calls.add('$event=$enabled');
    items = [
      for (final p in items) p.event == event ? p.withEnabled(enabled) : p,
    ];
    return items;
  }
}

class _Reads implements CustomerReadsRepository {
  final registered = <String>[];

  @override
  Future<void> registerDevice(String token, String platform) async {
    registered.add('$token/$platform');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Token implements PushTokenProvider {
  _Token(this.value);
  final String? value;

  @override
  String get platform => 'android';

  @override
  Future<String?> token() async => value;
}

class _CrewInbox implements CrewInboxRepository {
  var markedAll = false;
  final marked = <String>[];

  @override
  Future<CrewInbox> inbox() async => CrewInbox(
    unreadCount: markedAll ? 0 : 1,
    items: [
      CrewNotificationDto(
        id: 'c-1',
        event: 'crew_job_removed',
        title: 'Job removed',
        body: 'Cleaning-External for Creta MH12AB1234 on 07-Nov-26 is off.',
        createdAt: DateTime(2026, 11, 6, 9),
        read: false,
      ),
    ],
  );

  @override
  Future<void> markRead(String id) async => marked.add(id);

  @override
  Future<void> markAllRead() async => markedAll = true;
}

Future<void> _pump(
  WidgetTester tester,
  Widget screen,
  List<Override> overrides,
) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: customerTheme,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: screen,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

NotificationDto _n({String? visitId, String? refType, String? refId}) =>
    NotificationDto(
      id: 'n',
      event: 'x',
      title: 't',
      body: '',
      visitId: visitId,
      createdAt: DateTime(2026, 11, 1),
      read: false,
      refType: refType,
      refId: refId,
    );

void main() {
  group('where a notification opens', () {
    test('a visit, a payment, a complaint and the check-in', () {
      expect(
        NotificationPaths.of(_n(visitId: 'v-1')),
        '/customer/visit/v-1',
      );
      expect(
        NotificationPaths.of(_n(refType: 'payment', refId: 'p-1')),
        '/customer/pay/p-1',
      );
      expect(
        NotificationPaths.of(_n(refType: 'complaint', refId: 'c-1')),
        '/customer/support/complaints/c-1',
      );
      expect(
        NotificationPaths.of(_n(refType: 'checkin', refId: 's-1')),
        '/customer/support/checkin?subscription=s-1',
      );
      expect(NotificationPaths.of(_n()), isNull);
    });
  });

  group('settings', () {
    testWidgets('shows one switch for each event, all on', (tester) async {
      await _pump(tester, const SettingsScreen(), [
        notificationPrefsRepositoryProvider.overrideWithValue(_FakePrefs()),
      ]);
      expect(find.byType(SwitchListTile), findsNWidgets(5));
      for (final s in tester.widgetList<SwitchListTile>(
        find.byType(SwitchListTile),
      )) {
        expect(s.value, isTrue);
      }
      expect(find.text('Renewal reminder'), findsOneWidget);
    });

    testWidgets('a switch is saved on its own', (tester) async {
      final prefs = _FakePrefs();
      await _pump(tester, const SettingsScreen(), [
        notificationPrefsRepositoryProvider.overrideWithValue(prefs),
      ]);
      await tester.tap(find.text('Monthly check-in'));
      await tester.pumpAndSettle();
      expect(prefs.calls, ['monthly_check_in=false']);
      final off = tester
          .widgetList<SwitchListTile>(find.byType(SwitchListTile))
          .where((s) => !s.value);
      expect(off, hasLength(1));
    });
  });

  group('push registration', () {
    Future<_Reads> run(String? token, {bool signedIn = true}) async {
      final reads = _Reads();
      final container = ProviderContainer(
        overrides: [
          sessionStoreProvider.overrideWithValue(
            MemorySessionStore()..write(customerSession),
          ),
          authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
          customerReadsProvider.overrideWithValue(reads),
          pushTokenProvider.overrideWithValue(_Token(token)),
        ],
      );
      addTearDown(container.dispose);
      await container.read(authControllerProvider.future);
      await container.read(pushRegistrationProvider.future);
      return reads;
    }

    test('registers the token of a signed-in customer', () async {
      final reads = await run('fcm-token-1234');
      expect(reads.registered, ['fcm-token-1234/android']);
    });

    test('does nothing without a token', () async {
      final reads = await run(null);
      expect(reads.registered, isEmpty);
    });
  });

  group('crew inbox', () {
    testWidgets('lists messages and marks all read', (tester) async {
      final repo = _CrewInbox();
      await _pump(tester, const CrewNotificationsScreen(), [
        crewInboxRepositoryProvider.overrideWithValue(repo),
      ]);
      expect(find.text('Job removed'), findsOneWidget);
      await tester.tap(find.text('Mark all as read'));
      await tester.pumpAndSettle();
      expect(repo.markedAll, isTrue);
      expect(find.text('Mark all as read'), findsNothing);
    });

    testWidgets('a tap marks one read', (tester) async {
      final repo = _CrewInbox();
      await _pump(tester, const CrewNotificationsScreen(), [
        crewInboxRepositoryProvider.overrideWithValue(repo),
      ]);
      await tester.tap(find.text('Job removed'));
      await tester.pumpAndSettle();
      expect(repo.marked, ['c-1']);
    });
  });
}
