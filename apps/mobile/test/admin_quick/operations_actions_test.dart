import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/admin_quick/actions/actions_data.dart';
import 'package:priveo/features/admin_quick/actions/actions_screens.dart';
import 'package:priveo/l10n/app_localizations.dart';

class Adapter implements HttpClientAdapter {
  final writes = <RequestOptions>[];
  bool resolved = false;
  bool reject = false;
  String service = 'Cleaning-Internal';
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    Object body = [];
    var status = 200;
    if (options.method != 'GET') {
      writes.add(options);
      resolved = true;
      body = {};
      if (reject) {
        status = 409;
        body = {
          'code': 'retry_date_passed',
          'message': 'The next-day retry date has passed.',
        };
      }
    } else if (options.path.endsWith('/operations/jobs')) {
      body = [
        {
          'id': 'j1',
          'visit_id': 'visit1',
          'date': '2026-11-15',
          'service': service,
          'status': 'Could not complete',
          'registration': 'HR01ZZ1234',
          'customer_name': 'Asha Rao',
          'society': 'Meadows',
          'crew_name': 'Ravi',
          'reason': 'Other',
          'note': 'Car unavailable',
          'resolved_at': resolved ? '2026-11-15T10:00:00Z' : null,
          'outcome': resolved ? 'Reschedule' : null,
          'rescheduled_on': resolved ? '2026-11-16' : null,
          'replacement_assigned': false,
          'resolution_reason': '',
          'resolution_note': '',
          'resolved_by': 'Admin',
        },
      ];
    } else if (options.path.endsWith('/reasons')) {
      body = [
        {'key': 'other', 'label': 'Other'},
      ];
    } else if (options.path.endsWith('/directory/societies')) {
      body = [
        {'id': 's1', 'name': 'Meadows'},
      ];
    } else if (options.path == '/v1/admin/customers/c1') {
      body = {
        'first_name': 'Asha',
        'last_name': 'Rao',
        'email': 'asha@example.com',
        'mobile': '9876543210',
        'flat': 'A-12',
        'email_verified': true,
        'vehicles': [
          {
            'id': 'v1',
            'registration': 'HR01ZZ1234',
            'make': 'Tata',
            'model': 'Nexon',
            'society': 'Second society',
            'parking_basement': 'B2',
            'parking_number': '17',
            'payments': [],
            'subscription': {
              'status': 'Active',
              'plan_name': 'Premium',
              'price_rupees': 999,
            },
          },
        ],
      };
    } else if (options.path.endsWith('/changes')) {
      body = {
        'skips': [
          {'id': 'skip1', 'start_date': '2026-11-20'},
        ],
        'pauses': [
          {
            'id': 'pause1',
            'start_date': '2026-11-21',
            'end_date': '2026-11-22',
          },
        ],
        'renewal_date': '2026-12-01',
      };
    } else if (options.path == '/v1/admin/crew') {
      body = [
        {
          'id': 'crew1',
          'name': 'Ravi',
          'role': 'Member',
          'society': 'Meadows',
          'mobile': '9876543210',
          'active': true,
          'exceptions': [],
        },
      ];
    } else if (options.path == '/v1/admin/addons') {
      body = [
        {
          'service': 'Deep Spa',
          'vehicle': 'Nexon HR01ZZ1234',
          'customer_name': 'Asha',
          'society': 'Meadows',
          'date': '2026-11-15',
          'finish_by': '14:00',
          'status': 'Scheduled',
          'crew_name': 'Ravi',
          'start_time': '09:00',
          'payment_status': 'Due',
          'price_rupees': 1500,
          'standalone': false,
        },
      ];
    }
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Future<void> app(WidgetTester tester, Widget screen, Adapter adapter) async {
  tester.view.physicalSize = const Size(900, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final dio = Dio()..httpClientAdapter = adapter;
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        adminActionsRepositoryProvider.overrideWithValue(
          AdminActionsRepository(dio),
        ),
      ],
      child: MaterialApp(
        theme: adminTheme,
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

void main() {
  testWidgets('missed Interior is retried only through the next-day action', (
    tester,
  ) async {
    final adapter = Adapter();
    await app(tester, const AdminOperationsScreen(), adapter);
    await tester.enterText(
      find.widgetWithText(TextField, 'Outcome note'),
      'Customer confirmed availability',
    );
    await tester.tap(find.text('Reschedule for next day'));
    await tester.pumpAndSettle();
    expect(adapter.writes.single.path, '/v1/admin/operations/jobs/j1/resolve');
    expect(adapter.writes.single.data, {
      'action': 'Reschedule',
      'reason': '',
      'note': 'Customer confirmed availability',
    });
    expect(find.textContaining('Rescheduled on'), findsOneWidget);
    expect(find.textContaining('Needs scheduling'), findsOneWidget);
  });
  testWidgets('Exterior offers the extension skip and no retry', (
    tester,
  ) async {
    final adapter = Adapter()..service = 'Cleaning-External';
    await app(tester, const AdminOperationsScreen(), adapter);
    expect(find.text('Reschedule for next day'), findsNothing);
    expect(find.textContaining('Skipping adds one day'), findsOneWidget);
    await tester.tap(find.text('Skip job by operations'));
    await tester.pumpAndSettle();
    expect((adapter.writes.single.data as Map)['action'], 'Skip');
  });
  testWidgets('server rejection is visible to the admin', (tester) async {
    final adapter = Adapter()..reject = true;
    await app(tester, const AdminOperationsScreen(), adapter);
    await tester.tap(find.text('Reschedule for next day'));
    await tester.pumpAndSettle();
    expect(find.text('The next-day retry date has passed.'), findsOneWidget);
  });
  testWidgets(
    'customer quick actions use the existing skip and end-pause APIs',
    (tester) async {
      final adapter = Adapter();
      await app(tester, const AdminCustomerScreen(id: 'c1'), adapter);
      expect(find.textContaining('Second society'), findsOneWidget);
      await tester.tap(find.text('Skip date'));
      await tester.pumpAndSettle();
      expect(adapter.writes.last.path, '/v1/admin/vehicles/v1/skips');
      expect(
        (adapter.writes.last.data as Map)['date'],
        adminDate(DateTime.now().add(const Duration(days: 1))),
      );
      await tester.tap(find.text('End pause'));
      await tester.pumpAndSettle();
      expect(adapter.writes.last.path, '/v1/admin/vehicles/v1/pauses/pause1');
      expect(adapter.writes.last.method, 'DELETE');
      expect(find.text('Create customer'), findsNothing);
    },
  );
  testWidgets('crew exception uses the selected type and range', (
    tester,
  ) async {
    final adapter = Adapter();
    await app(tester, const AdminCrewScreen(), adapter);
    await tester.tap(find.text('Add crew exception'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sick'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Late start').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(adapter.writes.single.path, '/v1/admin/crew/crew1/exceptions');
    expect((adapter.writes.single.data as Map)['kind'], 'Late start');
    expect((adapter.writes.single.data as Map)['start'], '08:00');
  });
  testWidgets('add-on requests are read only and show assignment and payment', (
    tester,
  ) async {
    await app(tester, const AdminAddonsScreen(), Adapter());
    expect(find.text('Ravi 09:00'), findsOneWidget);
    expect(find.textContaining('Due'), findsOneWidget);
    expect(find.text('Request Deep Spa'), findsNothing);
  });
}
