import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/changes_money/data/money_models.dart';
import 'package:priveo/features/changes_money/routes.dart' as money_routes;

import 'fakes.dart';

SubscriptionDto _sub({
  String status = 'Active',
  bool canPayNext = false,
  int? listPrice,
  List<String> inclusions = const [],
  String? planCode,
}) => SubscriptionDto(
  vehicleId: vehicle,
  planName: 'Premium Care',
  vehicle: 'Hyundai Creta',
  registration: 'HR 26 DK 8337',
  society: 'DLF Meadows',
  status: status,
  monthlyPriceRupees: 999,
  paymentMethod: 'UPI',
  cutoffTime: '07:00',
  interiorDay: 'Friday',
  planInclusions: inclusions,
  planListPriceRupees: listPrice,
  planCode: planCode,
  cycleStart: d(8),
  cycleDays: 30,
  daysLeft: 12,
  latestPayment: payment('p0', status: 'Received'),
  canPayNext: canPayNext,
);

AddonRequestDto _addon(String id, String status, {String? vehicleId, int? price}) =>
    AddonRequestDto(
      id: id,
      service: 'Deep Spa',
      standalone: false,
      date: d(20),
      finishBy: '17:00',
      status: status,
      priceRupees: price,
      paymentId: null,
      paymentStatus: null,
      canChange: false,
      vehicleId: vehicleId,
    );

void main() {
  final path = money_routes.subscriptionPath(vehicle);

  group('My subscription details', () {
    testWidgets('shows what the plan includes, its list price and its ID', (tester) async {
      final repo = FakeMoneyRepository()
        ..sub = _sub(
          listPrice: 1499,
          inclusions: const ['Daily external cleaning', 'Weekly internal cleaning'],
          planCode: 'PLN-0001',
        );
      await openAt(tester, path, money: repo);
      expect(find.text('Daily external cleaning'), findsOneWidget);
      expect(find.text('Weekly internal cleaning'), findsOneWidget);
      expect(find.text('₹1,499'), findsOneWidget);
      expect(find.text('Plan ID: PLN-0001'), findsOneWidget);
      expect(find.textContaining('Expires on'), findsNothing);
    });

    testWidgets('Over due shows the end date and the Inactive warning (SUB-01)',
        (tester) async {
      final repo = FakeMoneyRepository()
        ..sub = SubscriptionDto(
          vehicleId: vehicle, planName: 'Premium Care', vehicle: 'Hyundai Creta',
          registration: 'HR 26 DK 8337', society: 'DLF', status: 'Active',
          monthlyPriceRupees: 999, paymentMethod: 'UPI', cutoffTime: null,
          interiorDay: null, cycleStart: d(1), cycleDays: 30, daysLeft: 0,
          cycleEnd: d(30), inactiveBy: d(7, 11), paymentId: 'p9',
          paymentStatus: 'Over due', daysToDue: -2,
          statusMessage: '2 days over due', lastPaymentFailed: true,
          latestPayment: payment('p9', status: 'Over due'), canPayNext: true,
        );
      await openAt(tester, path, money: repo);
      expect(find.text('Billing cycle ended on 30-Oct-26'), findsOneWidget);
      expect(
          find.text('Your subscription becomes Inactive if this is not paid by 07-Nov-26.'),
          findsOneWidget);
      expect(find.text('2 days over due'), findsOneWidget);
      expect(find.text('Your last payment failed'), findsOneWidget);
    });

    testWidgets('lists the open add-ons for this vehicle only', (tester) async {
      final repo = FakeMoneyRepository()
        ..sub = _sub()
        ..addonList = AddonsDto(
          offers: const [],
          requests: [
            _addon('a1', 'Scheduled', price: 1500),
            _addon('a2', 'Requested', vehicleId: vehicle),
            _addon('a3', 'Completed'),
            _addon('a4', 'Scheduled', vehicleId: 'other-vehicle'),
          ],
        );
      await openAt(tester, path, money: repo);
      // a1 and a2 are open and fit this vehicle; a3 is done and a4 is another car's.
      expect(find.text('Deep Spa'), findsNWidgets(2));
      expect(find.text('Scheduled'), findsOneWidget);
      expect(find.text('Requested'), findsOneWidget);
      expect(find.text('₹1,500'), findsOneWidget);
    });

    testWidgets('a paused plan offers pause and billing but not the defaults or add-ons', (
      tester,
    ) async {
      final repo = FakeMoneyRepository()..sub = _sub(status: 'Paused');
      await openAt(tester, path, money: repo);
      expect(find.text('Paused'), findsWidgets);
      expect(find.text('Pause service'), findsOneWidget);
      expect(find.text('View billing history'), findsOneWidget);
      expect(find.text('Change cutoff time or interior day'), findsNothing);
    });

    testWidgets('an inactive plan has no actions except billing history', (tester) async {
      final repo = FakeMoneyRepository()..sub = _sub(status: 'Inactive');
      await openAt(tester, path, money: repo);
      expect(find.text('Pause service'), findsNothing);
      expect(find.text('View billing history'), findsOneWidget);
    });
  });
}
