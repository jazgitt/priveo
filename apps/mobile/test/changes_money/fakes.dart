import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/api/api.g.dart' as wire;
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/features/support/widgets.dart' show LinkOpener, linkOpenerProvider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/admin_quick/payments/admin_payments_data.dart';
import 'package:priveo/features/admin_quick/payments/routes.dart' as admin_routes;
import 'package:priveo/features/changes_money/data/money_models.dart';
import 'package:priveo/features/changes_money/data/money_repository.dart';
import 'package:priveo/features/changes_money/routes.dart' as money_routes;
import 'package:priveo/l10n/app_localizations.dart';

const vehicle = 'v1';

DateTime d(int day, [int month = 10]) => DateTime(2026, month, day);

PaymentDto payment(String id,
        {String status = 'Due', int amount = 1299, String? invoice, DateTime? due}) =>
    PaymentDto(
      id: id,
      kind: 'Plan',
      description: 'Plan payment $id',
      amountRupees: amount,
      status: status,
      dueDate: due ?? d(7, 11),
      invoiceNumber: invoice,
    );

class FakeMoneyRepository implements MoneyRepository {
  final calls = <String>[];
  Object? failure;

  List<UpcomingDayDto> days = [
    for (var i = 12; i < 19; i++)
      UpcomingDayDto(
          date: d(i),
          services: i == 16
              ? const ['Cleaning-External', 'Cleaning-Internal']
              : const ['Cleaning-External'],
          state: i == 14 ? 'Skipped' : 'Scheduled',
          canChange: i != 12,
          skipId: i == 14 ? 'skip-14' : null),
  ];
  List<ChangeDto> pauses = [];
  SubscriptionDto sub = SubscriptionDto(
    vehicleId: vehicle,
    planName: 'Premium Care',
    vehicle: 'Hyundai Creta',
    registration: 'HR 26 DK 8337',
    society: 'DLF Meadows',
    status: 'Active',
    monthlyPriceRupees: 1299,
    paymentMethod: 'UPI',
    cutoffTime: '07:00',
    interiorDay: 'Friday',
    cycleStart: d(8),
    renewalDate: d(7, 11),
    cycleDays: 30,
    daysLeft: 26,
    latestPayment: payment('p0', status: 'Received'),
    canPayNext: true,
  );
  List<PaymentDto> history = [
    payment('p1'),
    payment('p0', status: 'Received', invoice: 'PRV102643210001', due: d(8)),
  ];
  /// The last day the plan covers (PAUSE-08); null leaves the dates unlimited.
  DateTime? planEndsOn;
  AddonsDto addonList = const AddonsDto(offers: [
    AddonOfferDto(
        service: 'Deep Spa',
        name: 'Deep Spa',
        description: 'A two-hour deep clean.',
        priceRupees: 1500,
        listPriceRupees: 2000,
        durationMinutes: 120),
  ], requests: []);

  void _check() {
    final f = failure;
    if (f != null) throw f;
  }

  @override
  Future<ChangesDto> changes(String v) async =>
      ChangesDto(skips: const [], pauses: pauses, planEndsOn: planEndsOn);

  @override
  Future<List<UpcomingDayDto>> upcoming(String v) async {
    _check();
    return days;
  }

  @override
  Future<ChangeDto> skip(String v, DateTime date) async {
    _check();
    calls.add('skip ${date.day}');
    return ChangeDto(
        id: 'skip-new',
        kind: 'skip',
        status: 'Active',
        startDate: date,
        endDate: date,
        days: 1);
  }

  @override
  Future<void> unskip(String v, String skipId) async {
    calls.add('unskip $skipId');
  }

  @override
  Future<ChangeDto> pause(String v, DateTime from, DateTime to) async {
    calls.add('pause ${from.day}-${to.day}');
    return ChangeDto(
        id: 'pause-new',
        kind: 'pause',
        status: 'Active',
        startDate: from,
        endDate: to,
        days: 7,
        visitsPaused: 7,
        renewalDate: d(14, 11));
  }

  @override
  Future<ChangeDto> endPause(String v, String pauseId) async {
    calls.add('endPause $pauseId');
    pauses = [];
    return ChangeDto(
        id: pauseId,
        kind: 'pause',
        status: 'Active',
        startDate: d(12),
        endDate: d(14),
        days: 3);
  }

  @override
  Future<SubscriptionDto> subscription(String v) async => sub;

  @override
  Future<List<PaymentDto>> payments(String v) async => history;

  @override
  Future<PaymentDetailDto> paymentDetail(String id) async => PaymentDetailDto(
        payment: payment(id, amount: id == 'p-addon' ? 1500 : 1299),
        instructions: PayInstructionsDto(
            amountRupees: id == 'p-addon' ? 1500 : 1299,
            upiId: 'priveo-placeholder@upi',
            upiUri: 'upi://pay?pa=priveo-placeholder@upi&am=${id == 'p-addon' ? 1500 : 1299}&cu=INR',
            payeeName: 'Priveo (placeholder)'),
      );

  @override
  Future<PaymentDetailDto> payNext(String v) async {
    calls.add('payNext');
    return paymentDetail('p-next');
  }

  @override
  Future<PaymentDetailDto> markPaid(String id) async {
    _check();
    calls.add('paid $id');
    return PaymentDetailDto(
        vehicle: 'HR01ZZ1234 · Hyundai Creta SX',
        serviceDetails: const {'cutoff_time': '07:00', 'interior_day': 'Friday'},
        payment: payment(id, status: 'Initiated'),
        instructions: const PayInstructionsDto(
            amountRupees: 1299, upiId: 'x@upi', payeeName: 'Priveo'));
  }

  @override
  Future<InvoiceDto> invoice(String id) async => InvoiceDto(
      number: 'PRV102643210001',
      issuedOn: d(8),
      amountRupees: 1299,
      description: 'Plan payment',
      customerName: 'Meera Rao',
      sellerName: 'Priveo (placeholder seller)',
      sellerGstin: '00PLACEHOLDER0Z0');

  @override
  Future<AddonsDto> addons() async => addonList;

  @override
  Future<AddonRequestDto> requestAddon(
      String v, DateTime date, String finishBy,
      {String addon = '', String service = 'Deep Spa'}) async {
    calls.add('addon ${date.day} $finishBy${addon.isEmpty ? '' : ' $addon'}');
    return AddonRequestDto(
        id: 'a1',
        service: service,
        standalone: false,
        date: date,
        finishBy: finishBy,
        status: 'Requested',
        priceRupees: 1500,
        paymentId: 'p-addon',
        paymentStatus: 'Due',
        canChange: true);
  }

  @override
  Future<AddonRequestDto> requestStandalone(
      {String? vehicleId,
      required DateTime date,
      required String finishBy,
      required String mobile,
      required String notes,
      String addon = '',
      String service = 'Deep Spa'}) async {
    calls.add('standalone $mobile${addon.isEmpty ? '' : ' $addon'}');
    return AddonRequestDto(
        id: 'a2',
        service: 'Deep Spa',
        standalone: true,
        date: date,
        finishBy: finishBy,
        status: 'Requested',
        priceRupees: 1500,
        paymentId: 'p-addon',
        paymentStatus: 'Due',
        canChange: true);
  }

  @override
  Future<AddonRequestDto> cancelAddon(String id) async {
    calls.add('cancelAddon $id');
    return AddonRequestDto(
        id: id,
        service: 'Deep Spa',
        standalone: false,
        date: d(20),
        finishBy: '12:00',
        status: 'Cancelled',
        priceRupees: 1500,
        paymentId: 'p-addon',
        paymentStatus: null,
        canChange: false);
  }
}

class FakeAdminPaymentsRepository implements AdminPaymentsRepository {
  final calls = <String>[];
  List<AdminPaymentDto> pending = [
    AdminPaymentDto(
        id: 'pay-1',
        kind: 'Plan',
        description: 'Plan 31-Oct-26',
        amountRupees: 1299,
        status: 'Initiated',
        dueDate: DateTime(2026, 10, 31),
        customerName: 'Meera Rao',
        flat: 'A-101',
        vehicle: 'Hyundai Creta HR 26 DK 8337'),
  ];
  List<AdminAlertDto> alertList = [
    AdminAlertDto(
        id: 'al-1',
        kind: 'auto_inactive',
        message: "Meera Rao's subscription is Inactive.",
        createdAt: DateTime.utc(2026, 10, 28),
        read: false),
  ];

  @override
  Future<List<AdminPaymentDto>> toConfirm() async => pending;

  @override
  Future<void> confirm(String id) async {
    calls.add('confirm $id');
    pending = pending.where((p) => p.id != id).toList();
  }

  @override
  Future<void> reject(String id) async {
    calls.add('reject $id');
    pending = pending.where((p) => p.id != id).toList();
  }

  @override
  Future<List<AdminAlertDto>> alerts() async => alertList;

  @override
  Future<void> markRead(String id) async {
    calls.add('read $id');
    alertList = [
      for (final a in alertList)
        AdminAlertDto(
            id: a.id, kind: a.kind, message: a.message, createdAt: a.createdAt, read: true),
    ];
  }
}

const apiDown = ApiFailure(code: 'after_cutoff', message: 'Changes for 12-Oct-26 closed at 9 PM the evening before. Please call support.', statusCode: 409);

/// Opens [path] in a router made of the slice's own route lists.
Future<void> openAt(
  WidgetTester tester,
  String path, {
  FakeMoneyRepository? money,
  FakeAdminPaymentsRepository? admin,
  Dio? dio,
  wire.PriveoApi? api,
  LinkOpener? linkOpener,
}) async {
  tester.view.physicalSize = const Size(900, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final router = GoRouter(
    initialLocation: path,
    routes: [
      GoRoute(path: '/customer', builder: (_, _) => const Scaffold(body: Text('HOME'))),
      ...money_routes.routes,
      ...admin_routes.routes,
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(ProviderScope(
    retry: (_, _) => null,
    overrides: [
      if (dio != null) dioProvider.overrideWithValue(dio),
      if (api != null) apiProvider.overrideWithValue(api),
      if (linkOpener != null) linkOpenerProvider.overrideWithValue(linkOpener),
      readRefreshProvider.overrideWith((_) => const Stream<int>.empty()),
      moneyRepositoryProvider.overrideWithValue(money ?? FakeMoneyRepository()),
      adminPaymentsRepositoryProvider
          .overrideWithValue(admin ?? FakeAdminPaymentsRepository()),
    ],
    child: MaterialApp.router(
      theme: customerTheme,
      routerConfig: router,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
    ),
  ));
  await tester.pumpAndSettle();
}
