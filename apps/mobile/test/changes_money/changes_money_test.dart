// Changes and money: skip and pause (SKIP-, PAUSE-), My Subscription (SUB-),
// billing history, the UPI screen (PAY-05 to PAY-09), Deep Spa (ADD-), and
// the admin's payment confirmation. Fake repositories, no network.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/changes_money/data/money_models.dart';
import 'package:priveo/features/changes_money/money_widgets.dart';
import 'package:priveo/features/changes_money/routes.dart';

import 'fakes.dart';

void main() {
  group('units', () {
    test('payment status labels follow PAY-09', () {
      expect(paymentStatusLabel(payment('a')), 'Due by 07-Nov-26');
      expect(paymentStatusLabel(payment('a', status: 'Over due')), 'Over due');
      expect(paymentStatusLabel(payment('a', status: 'Initiated')), 'Initiated');
      expect(paymentStatusLabel(payment('a', status: 'Received')), 'Received');
    });

    test('finish-by times are in 30-minute steps', () {
      final steps = halfHourSteps();
      expect(steps.length, 48);
      expect(steps.first, '00:00');
      expect(steps[13], '06:30');
      expect(steps.last, '23:30');
    });

    test('a subscription reads from the API shape', () {
      final s = SubscriptionDto.fromJson({
        'vehicle_id': 'v',
        'subscription_id': 's',
        'plan_name': null,
        'vehicle': 'Swift',
        'registration': '',
        'society': 'DLF',
        'status': 'Paused',
        'monthly_price_rupees': 999,
        'payment_method': 'UPI',
        'cutoff_time': null,
        'interior_day': null,
        'cycle_start': '2026-10-01',
        'renewal_date': '2026-10-31',
        'cycle_days': 30,
        'days_left': 20,
        'latest_payment': null,
        'can_pay_next': false,
      });
      expect((s.status, s.daysLeft, s.renewalDate), ('Paused', 20, DateTime(2026, 10, 31)));
    });

    test('route paths', () {
      expect(payPath('p1'), '/customer/pay/p1');
      expect(standalonePath('v1'), '/customer/deep-spa?vehicle=v1');
      expect(routes.length, 6);
    });
  });

  group('skip and pause', () {
    testWidgets('skip with no date says to pick one first', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, skipPausePath(vehicle), money: repo);
      await tester.tap(find.text('Confirm skip'));
      await tester.pumpAndSettle();
      expect(find.text('Pick a date to skip first.'), findsOneWidget);
      expect(repo.calls, isEmpty);
    });

    testWidgets('skip a date, with the note and a confirmation', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, skipPausePath(vehicle), money: repo);
      await tester.tap(find.text('15').first);
      await tester.pumpAndSettle();
      expect(find.text("No cleaning on 15-Oct-26. Your plan isn't charged for this visit."),
          findsOneWidget);
      await tester.tap(find.text('Confirm skip'));
      await tester.pumpAndSettle();
      expect(repo.calls, ['skip 15']);
      expect(find.text('Skipped 15-Oct-26. The crew has been told.'), findsOneWidget);
    });

    testWidgets('a skipped date can be undone', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, skipPausePath(vehicle), money: repo);
      await tester.tap(find.text('14').first);
      await tester.pumpAndSettle();
      expect(find.text('Undo skip'), findsOneWidget);
      await tester.tap(find.text('Undo skip'));
      await tester.pumpAndSettle();
      expect(repo.calls, ['unskip skip-14']);
    });

    testWidgets('a date past its 9 PM cutoff cannot be picked', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, skipPausePath(vehicle), money: repo);
      await tester.tap(find.text('12').first, warnIfMissed: false);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Confirm skip'));
      await tester.pumpAndSettle();
      expect(find.text('Pick a date to skip first.'), findsOneWidget);
    });

    testWidgets("the server's cutoff message is shown", (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, skipPausePath(vehicle), money: repo);
      await tester.tap(find.text('13').first);
      await tester.pumpAndSettle();
      repo.failure = apiDown;
      await tester.tap(find.text('Confirm skip'));
      await tester.pumpAndSettle();
      expect(find.textContaining('closed at 9 PM the evening before'), findsOneWidget);
    });

    testWidgets('pause needs both dates', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, skipPausePath(vehicle), money: repo);
      await tester.tap(find.text('Pause').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Confirm pause'));
      await tester.pumpAndSettle();
      expect(find.text('Choose the start and end dates first.'), findsOneWidget);
      expect(repo.calls, isEmpty);
    });

    testWidgets('a running pause can be ended', (tester) async {
      final repo = FakeMoneyRepository()
        ..pauses = [
          ChangeDto(
              id: 'pz',
              kind: 'pause',
              status: 'Active',
              startDate: d(12),
              endDate: d(25),
              days: 14),
        ];
      await openAt(tester, skipPausePath(vehicle), money: repo);
      await tester.tap(find.text('Pause').first);
      await tester.pumpAndSettle();
      expect(find.text('12-Oct-26 to 25-Oct-26'), findsOneWidget);
      await tester.tap(find.text('End pause'));
      await tester.pumpAndSettle();
      expect(repo.calls, ['endPause pz']);
    });
  });

  group('subscription and billing', () {
    testWidgets('My subscription shows the cycle and the latest payment', (tester) async {
      await openAt(tester, subscriptionPath(vehicle));
      expect(find.text('Premium Care'), findsOneWidget);
      expect(find.text('Active'), findsOneWidget);
      expect(find.text('26 days left'), findsOneWidget);
      expect(find.text('Monthly amount: ₹1,299'), findsOneWidget);
      expect(find.text('Payment method: UPI'), findsOneWidget);
      expect(find.text('Received'), findsOneWidget);
      expect(find.text('Pay for next month'), findsOneWidget);
    });

    testWidgets('pay for next month opens the UPI screen', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, subscriptionPath(vehicle), money: repo);
      await tester.tap(find.text('Pay for next month'));
      await tester.pumpAndSettle();
      expect(repo.calls, ['payNext']);
      expect(find.text('Pay by UPI'), findsOneWidget);
      expect(find.text('priveo-placeholder@upi'), findsOneWidget);
    });

    testWidgets('no pay button when the payment is not open', (tester) async {
      final repo = FakeMoneyRepository();
      repo.sub = SubscriptionDto(
        vehicleId: vehicle, planName: null, vehicle: 'Swift', registration: '',
        society: 'DLF', status: 'Inactive', monthlyPriceRupees: 999, paymentMethod: 'UPI',
        cutoffTime: null, interiorDay: null, cycleStart: d(1), renewalDate: d(31),
        cycleDays: 30, daysLeft: 0, latestPayment: payment('p9', status: 'Over due'),
        canPayNext: false,
      );
      await openAt(tester, subscriptionPath(vehicle), money: repo);
      expect(find.text('Pay for next month'), findsNothing);
      expect(find.text('Inactive'), findsOneWidget);
      expect(find.text('Over due'), findsOneWidget);
      expect(find.text('Pause service'), findsNothing);
    });

    testWidgets('billing history lists newest first with an invoice', (tester) async {
      await openAt(tester, billingPath(vehicle));
      expect(find.text('Due by 07-Nov-26'), findsOneWidget);
      expect(find.text('Received'), findsOneWidget);
      await tester.tap(find.text('Invoice'));
      await tester.pumpAndSettle();
      expect(find.text('PRV102643210001'), findsOneWidget);
      expect(find.text('Price includes GST.'), findsOneWidget);
    });
  });

  group('pay by UPI', () {
    testWidgets("I've paid submits and shows Initiated (PAY-06, PAY-07)", (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, payPath('p1'), money: repo);
      expect(find.text('Amount to pay: ₹1,299'), findsOneWidget);
      expect(find.text('The UPI QR code will be shown here.'), findsOneWidget);
      await tester.tap(find.text("I've paid"));
      await tester.pumpAndSettle();
      expect(repo.calls, ['paid p1']);
      expect(find.text('Payment submitted'), findsWidgets);
      expect(find.text('Initiated'), findsOneWidget);
      expect(find.text('Go to home'), findsOneWidget);
      await tester.tap(find.text('Go to home'));
      await tester.pumpAndSettle();
      expect(find.text('HOME'), findsOneWidget);
    });
  });

  group('Deep Spa', () {
    testWidgets('a date is required before Confirm & pay', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, addonsPath(vehicle), money: repo);
      expect(find.text('₹1,500'), findsOneWidget);
      expect(find.text('2 hours'), findsOneWidget);
      await tester.tap(find.text('Confirm & pay'));
      await tester.pumpAndSettle();
      expect(find.text('Choose a date'), findsOneWidget);
      expect(repo.calls, isEmpty);
    });

    testWidgets('earlier requests show their status and can be cancelled', (tester) async {
      final repo = FakeMoneyRepository();
      repo.addonList = AddonsDto(offers: repo.addonList.offers, requests: [
        AddonRequestDto(
            id: 'a1', service: 'Deep Spa', standalone: false, date: d(20),
            finishBy: '12:30', status: 'Requested', priceRupees: 1500,
            paymentId: 'p-addon', paymentStatus: 'Due', canChange: true),
      ]);
      await openAt(tester, addonsPath(vehicle), money: repo);
      await tester.scrollUntilVisible(find.text('Cancel request'), 300,
          scrollable: find.byType(Scrollable).first);
      expect(find.text('Requested'), findsOneWidget);
      expect(find.text('Deep Spa, 20-Oct-26'), findsOneWidget);
      await tester.tap(find.text('Cancel request'));
      await tester.pumpAndSettle();
      expect(repo.calls, ['cancelAddon a1']);
    });

    testWidgets('standalone Deep Spa is a request with a number to call', (tester) async {
      final repo = FakeMoneyRepository();
      await openAt(tester, standalonePath(), money: repo);
      expect(find.textContaining('Priveo will call you to agree'), findsOneWidget);
      await tester.tap(find.text('Send request'));
      await tester.pumpAndSettle();
      expect(find.text('Choose a date'), findsOneWidget);
      expect(repo.calls, isEmpty);
    });
  });

  group('admin quick actions', () {
    testWidgets('confirm a payment', (tester) async {
      final admin = FakeAdminPaymentsRepository();
      await openAt(tester, '/admin/payments', admin: admin);
      expect(find.text('Meera Rao, A-101'), findsOneWidget);
      expect(find.text('₹1,299'), findsOneWidget);
      await tester.tap(find.text('Confirm'));
      await tester.pumpAndSettle();
      expect(admin.calls, ['confirm pay-1']);
      expect(find.text('Nothing to confirm.'), findsOneWidget);
    });

    testWidgets('reject sends the payment back', (tester) async {
      final admin = FakeAdminPaymentsRepository();
      await openAt(tester, '/admin/payments', admin: admin);
      await tester.tap(find.text('Reject'));
      await tester.pumpAndSettle();
      expect(admin.calls, ['reject pay-1']);
    });

    testWidgets('alerts can be marked read', (tester) async {
      final admin = FakeAdminPaymentsRepository();
      await openAt(tester, '/admin/payment-alerts', admin: admin);
      expect(find.text("Meera Rao's subscription is Inactive."), findsOneWidget);
      await tester.tap(find.text('Mark read'));
      await tester.pumpAndSettle();
      expect(admin.calls, ['read al-1']);
      expect(find.text('Mark read'), findsNothing);
    });
  });
}
