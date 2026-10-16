// Customer flows beyond sign-in on the real screens against the real fixture
// API: subscription and billing (SUB, PAY), service history, account,
// notifications and settings (ACC, SET, NOTIF, HIST). Each test names the
// scenario it uses; a test that changes data uses a scenario no other test
// changes. Needs the fixture API; see scenario_screens_test.dart.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario customer', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }
  setUpAll(() => HttpOverrides.global = null);
  final scenarios = loadScenarios();
  String customer(String id) => scenarios[id]!['customer_login'] as String;

  Future<void> home(WidgetTester tester, String id) async {
    await openApp(
      tester,
      await signInApi(tester, customer(id), scenarioPassword),
    );
    await untilFound(tester, find.byType(GreetingLine));
  }

  Future<void> openSubscription(WidgetTester tester, String id) async {
    await home(tester, id);
    await tapFinder(tester, find.text('My subscription'));
    await untilFound(tester, find.text('LATEST PAYMENT'));
  }

  group('subscription and billing', () {
    testWidgets('C09 shows the plan, the cycle and a payment that is due', (
      tester,
    ) async {
      await openSubscription(tester, 'C09');
      expect(find.text('Active'), findsWidgets);
      expect(find.text('Monthly amount: ₹999'), findsOneWidget);
      expect(find.text('Payment method: UPI'), findsOneWidget);
      expect(find.textContaining('days left'), findsOneWidget);
      expect(find.textContaining('Billing cycle:'), findsOneWidget);
      expect(find.textContaining('Due by'), findsOneWidget);
      expect(find.text('Renew subscription'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C24 has paid, so there is nothing to pay', (tester) async {
      await openSubscription(tester, 'C24');
      expect(find.text('Received'), findsOneWidget);
      expect(find.text('Pay for next month'), findsNothing);
      expect(find.text('Change cutoff time or interior day'), findsOneWidget);
      expect(find.text('Pause service'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C20 is Inactive with an Over due payment and no actions', (
      tester,
    ) async {
      await openSubscription(tester, 'C20');
      expect(find.text('Inactive'), findsWidgets);
      expect(find.text('Over due'), findsOneWidget);
      expect(find.text('Pause service'), findsNothing);
      expect(find.text('Change cutoff time or interior day'), findsNothing);
      await letTimersFinish(tester);
    });

    testWidgets('C27 migrated data still shows a plan and a receipt', (
      tester,
    ) async {
      await openSubscription(tester, 'C27');
      expect(find.text('Active'), findsWidgets);
      expect(find.text('Received'), findsOneWidget);
      expect(find.text('Monthly amount: ₹999'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C09 pays by UPI: the screen shows the amount and the UPI ID', (
      tester,
    ) async {
      await openSubscription(tester, 'C09');
      await tapFinder(tester, find.text('Pay for next month'));
      await untilFound(tester, find.text('Amount to pay: ₹999'));
      expect(find.textContaining('Due by'), findsWidgets);
      expect(find.text('UPI ID'), findsOneWidget);
      expect(find.text("I've paid"), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C09 billing history lists the cycle payment', (tester) async {
      await openSubscription(tester, 'C09');
      await tapFinder(tester, find.text('View billing history'));
      await untilFound(tester, find.text('TEST plan cycle'));
      expect(find.text('₹999'), findsWidgets);
      await letTimersFinish(tester);
    });

    testWidgets('C24 opens its service defaults', (tester) async {
      await openSubscription(tester, 'C24');
      await tapFinder(tester, find.text('Change cutoff time or interior day'));
      await untilFound(tester, find.text('Service defaults'));
      expect(find.text('Cutoff time: 11:00 AM'), findsOneWidget);
      expect(find.text('Interior care day'), findsOneWidget);
      expect(find.text('Save'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });

  group('service history', () {
    testWidgets('C22 lists a rated, completed clean', (tester) async {
      await home(tester, 'C22');
      await tapFinder(tester, find.text('Service History'));
      await untilFound(tester, find.text('Cleaning-External'));
      await untilFound(tester, find.text('5 stars'));
      expect(find.text('Completed'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C03 lists a completed Deep Spa that is not rated yet', (
      tester,
    ) async {
      await home(tester, 'C03');
      await tapFinder(tester, find.text('Service History'));
      await untilFound(tester, find.text('Deep Spa'));
      await untilFound(tester, find.text('Not rated'));
      expect(find.text('Completed'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C09 has no services this month', (tester) async {
      await home(tester, 'C09');
      await tapFinder(tester, find.text('Service History'));
      await untilFound(tester, find.text('No services in this month.'));
      await letTimersFinish(tester);
    });

    testWidgets('C22 has nothing to rate today', (tester) async {
      await home(tester, 'C22');
      await tapFinder(tester, find.text("Rate today's clean"));
      await untilFound(tester, find.text('No completed clean to rate today.'));
      await letTimersFinish(tester);
    });
  });

  group('calendar', () {
    testWidgets('C09 shows the month, the legend and when the plan renews', (
      tester,
    ) async {
      await home(tester, 'C09');
      await tapFinder(tester, find.text('Calendar'));
      await untilFound(tester, find.text('Service calendar'));
      for (final label in [
        'Completed',
        'Scheduled',
        'Skipped',
        'Missed',
        'Paused',
        'Deep Spa',
      ]) {
        expect(find.text(label), findsWidgets, reason: 'legend "$label"');
      }
      await untilFound(tester, find.textContaining('Your plan renews on'));
      await letTimersFinish(tester);
    });
  });

  group('account', () {
    testWidgets('C26 lists both vehicles, one in each society', (tester) async {
      await home(tester, 'C26');
      await tapFinder(tester, find.text('Account'));
      await untilFound(tester, find.text('My account'));
      expect(find.text('Creta · TS 26 TT 0001'), findsOneWidget);
      expect(find.text('Creta · TS 26 TT 0002'), findsOneWidget);
      expect(
        find.textContaining('TEST C26 Vehicles in two societies'),
        findsOneWidget,
      );
      expect(find.textContaining('TEST Secondary Society'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C29 has one unread and one read notification', (tester) async {
      await home(tester, 'C29');
      await tapFinder(tester, find.text('Account'));
      await tapFinder(tester, find.text('Notifications'));
      await untilFound(tester, find.text('TEST Unread service message'));
      expect(find.text('TEST Read service message'), findsOneWidget);
      expect(find.text('Mark all as read'), findsOneWidget);
      await letTimersFinish(tester);
    });

    testWidgets('C25 has no notifications; the password form shows its rule', (
      tester,
    ) async {
      await home(tester, 'C25');
      await tapFinder(tester, find.text('Account'));
      await tapFinder(tester, find.text('Notifications'));
      await untilFound(tester, find.text('No notifications yet.'));
      await tester.pageBack();
      await tester.pump(const Duration(milliseconds: 500));
      await tapFinder(tester, find.text('Change password'));
      await untilFound(tester, find.text('Current password'));
      expect(find.text('New password'), findsOneWidget);
      expect(
        find.text('Use at least 8 characters, with a letter and a number.'),
        findsOneWidget,
      );
      await letTimersFinish(tester);
    });
  });

  group('support', () {
    testWidgets('C25 support shows the contacts, hours and help entries', (
      tester,
    ) async {
      await home(tester, 'C25');
      await tapFinder(tester, find.text('Support'));
      await untilFound(tester, find.text('Call support'));
      expect(find.text('WhatsApp support'), findsOneWidget);
      expect(find.text('Support hours: 6 AM to 10 PM'), findsOneWidget);
      expect(find.text('Frequently asked questions'), findsOneWidget);
      expect(find.text('Report an issue'), findsOneWidget);
      expect(find.text('My complaints'), findsOneWidget);
      expect(find.text('Give feedback'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });
}
