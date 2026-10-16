// The customer's home with its vehicle cards (HOME-07) and the review of
// their details at first sign-in (ONB-25, ONB-26).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/features/customer/home/car_illustration.dart';
import 'package:priveo/features/customer/home/customer_home_data.dart';
import 'package:priveo/features/customer/onboarding/onboarding_review_screen.dart';
import 'package:priveo/core/routing/router.dart';
import 'package:priveo/features/support/feedback_tab.dart';
import 'package:priveo/features/support/routes.dart' show SupportRoutes;

import 'support/fakes.dart';

Future<FakePriveoApi> openAsCustomer(
  WidgetTester tester, {
  bool confirmed = true,
  bool hasPhoto = true,
}) async {
  // A tall phone, so a whole step is on screen.
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final store = MemorySessionStore();
  await store.write(customerSession);
  final api = FakePriveoApi(onboardingConfirmed: confirmed);
  await pumpApp(
    tester,
    store: store,
    api: api,
    account: PhotoAccount(hasPhoto: hasPhoto),
  );
  await passSplash(tester);
  return api;
}

Future<void> next(WidgetTester tester, [String label = 'Continue']) async {
  await tester.tap(find.text(label));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('feedback tab follows a post-onboarding customer onto detail routes', (tester) async {
    await openAsCustomer(tester);
    expect(find.byType(FeedbackSideTab), findsOneWidget);
    final container = ProviderScope.containerOf(tester.element(find.byType(FeedbackSideTab)));
    container.read(routerProvider).push(SupportRoutes.faq);
    await tester.pumpAndSettle();
    expect(find.byType(FeedbackSideTab), findsOneWidget);
    expect(find.text('How does billing work?'), findsOneWidget);
  });
  group('home', () {
    testWidgets('shows the first vehicle and its service details',
        (tester) async {
      await openAsCustomer(tester);
      expect(find.text('Hyundai Creta'), findsOneWidget);
      expect(find.text('MH 12 AB 1234'), findsOneWidget);
      expect(find.text('₹1,299 a month'), findsOneWidget);
      expect(find.text('07-Nov-26'), findsOneWidget);
      expect(find.text('Planned before your cutoff time - 7:00 AM'), findsOneWidget);
      expect(find.text('Interior care on Friday'), findsOneWidget);
      expect(find.bySemanticsLabel('Vehicle 1 of 3'), findsOneWidget);
    });

    testWidgets('one card holds image, plan name and next service; the calendar button is outside it',
        (tester) async {
      await openAsCustomer(tester);
      // No vehicle photo: the default car illustration shows.
      expect(find.byType(CarIllustration), findsWidgets);
      expect(find.text('Daily Premium'), findsOneWidget);
      final nextService = find.text('Planned before your cutoff time - 7:00 AM');
      expect(find.ancestor(of: nextService, matching: find.byType(Card)), findsWidgets);
      final calendar = find.text('View service calendar');
      expect(calendar, findsOneWidget);
      expect(find.ancestor(of: calendar, matching: find.byType(Card)), findsNothing);
    });

    testWidgets('swiping selects the next vehicle', (tester) async {
      await openAsCustomer(tester);
      final container =
          ProviderScope.containerOf(tester.element(find.byType(PageView)));

      await tester.drag(find.byType(PageView), const Offset(-320, 0));
      await tester.pumpAndSettle();
      expect(container.read(selectedVehicleProvider), 'v2');
      expect(find.bySemanticsLabel('Vehicle 2 of 3'), findsOneWidget);
      // The gaps in the record are said plainly, and nothing is scheduled.
      expect(find.text('Number to be added'), findsOneWidget);
      expect(find.text('Parking to be added'), findsOneWidget);
      expect(find.text('Not scheduled yet'), findsOneWidget);
      expect(find.text('Planned before your cutoff time - 6:30 AM'), findsOneWidget);
      expect(find.text('07-Nov-26'), findsNothing);

      // A vehicle with no subscription has no service card.
      await tester.drag(find.byType(PageView), const Offset(-320, 0));
      await tester.pumpAndSettle();
      expect(container.read(selectedVehicleProvider), 'v3');
      expect(find.text('No subscription'), findsOneWidget);
      expect(find.text('No plan'), findsOneWidget);
      expect(find.text('Next service'.toUpperCase()), findsNothing);
      expect(find.text('Skip or Pause'), findsNothing);
      expect(find.text('Deep Spa'), findsWidgets);
    });

    testWidgets('the selection is kept when Home is opened again',
        (tester) async {
      await openAsCustomer(tester);
      await tester.drag(find.byType(PageView), const Offset(-320, 0));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Calendar'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Home'));
      await tester.pumpAndSettle();
      expect(find.bySemanticsLabel('Vehicle 2 of 3'), findsOneWidget);
      expect(find.text('Not scheduled yet'), findsOneWidget);
    });
  });

  test('cutoff times are every half hour of the day', () {
    expect(cutoffTimes, hasLength(48));
    expect(cutoffTimes.first, '00:00');
    expect(cutoffTimes[13], '06:30');
    expect(cutoffTimes.last, '23:30');
  });
}
