// The customer's home with its vehicle cards (HOME-07) and the review of
// their details at first sign-in (ONB-25, ONB-26).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/features/customer/home/customer_home_data.dart';
import 'package:priveo/features/customer/onboarding/onboarding_review_screen.dart';

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
  group('home', () {
    testWidgets('shows the first vehicle and its service details',
        (tester) async {
      await openAsCustomer(tester);
      expect(find.text('Hyundai Creta'), findsOneWidget);
      expect(find.text('MH 12 AB 1234'), findsOneWidget);
      expect(find.text('₹1,299 a month'), findsOneWidget);
      expect(find.text('07-Nov-26'), findsOneWidget);
      expect(find.text('Daily clean by 7:00 AM'), findsOneWidget);
      expect(find.text('Interior care on Friday'), findsOneWidget);
      expect(find.bySemanticsLabel('Vehicle 1 of 3'), findsOneWidget);
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
      expect(find.text('Daily clean by 6:30 AM'), findsOneWidget);
      expect(find.text('07-Nov-26'), findsNothing);

      // A vehicle with no subscription has no service card.
      await tester.drag(find.byType(PageView), const Offset(-320, 0));
      await tester.pumpAndSettle();
      expect(container.read(selectedVehicleProvider), 'v3');
      expect(find.text('No subscription'), findsOneWidget);
      expect(find.text('No plan'), findsOneWidget);
      expect(find.text('Next service'.toUpperCase()), findsNothing);
      expect(find.text('Skip or Pause'), findsOneWidget);
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

  group('review at first sign-in', () {
    testWidgets('opens in place of Home, with what the admin entered',
        (tester) async {
      await openAsCustomer(tester, confirmed: false);
      expect(find.byType(OnboardingReviewScreen), findsOneWidget);
      expect(find.text('Step 1 of 6'), findsOneWidget);
      expect(find.text('Your details'), findsOneWidget);
      expect(find.text('aarav@gmale.com'), findsOneWidget);
      expect(find.textContaining(RegExp(r'^Good (morning|afternoon|evening),$')), findsNothing);
    });

    testWidgets('the customer fills the gaps, confirms and reaches Home',
        (tester) async {
      final api = await openAsCustomer(tester, confirmed: false);

      // Details: the last name is missing.
      await next(tester);
      expect(find.text('Enter your last name, using letters only.'),
          findsOneWidget);
      expect(find.text('Step 1 of 6'), findsOneWidget);
      await tester.enterText(find.byType(TextField).at(1), 'Mehta');
      await next(tester);

      // Society: read-only.
      expect(find.text('Your society'), findsOneWidget);
      expect(find.text('Green Meadows'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
      await next(tester);

      // First car: complete. The customer changes the interior day.
      expect(find.text('Vehicle 1 of 3'), findsOneWidget);
      expect(find.text('Your spot: B2 · 14'), findsOneWidget);
      expect(find.text('7:00 AM'), findsOneWidget);
      // The photo above pushes the day pills down: scroll them clear of the bar.
      await tester.drag(find.byType(ListView).first, const Offset(0, -250));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sun'));
      await tester.pumpAndSettle();
      await next(tester);

      // Second car: parking and cutoff time are missing. No interior day.
      expect(find.text('Vehicle 2 of 3'), findsOneWidget);
      expect(find.text('Interior care day'), findsNothing);
      await next(tester);
      expect(find.text('Select the basement.'), findsOneWidget);
      expect(find.text('Enter the parking number, in digits.'), findsOneWidget);
      expect(find.text('Please select your service cutoff time.'),
          findsOneWidget);
      await tester.tap(find.text('B3'));
      await tester.enterText(find.byType(TextField), '12a7');
      await tester.pumpAndSettle();
      expect(find.text('Your spot: B3 · 127'), findsOneWidget);
      await tester.tap(find.text('Choose a time'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('6:30 AM'));
      await tester.pumpAndSettle();
      await next(tester);

      // Third car: no subscription, so only the parking is asked.
      expect(find.text('Vehicle 3 of 3'), findsOneWidget);
      expect(find.text('Service cutoff time'), findsNothing);
      await next(tester);

      expect(find.text('Review and confirm'), findsOneWidget);
      expect(find.text('Aarav Mehta'), findsOneWidget);
      expect(find.text('B3-127'), findsOneWidget);
      expect(find.text('Sunday'), findsOneWidget);
      await next(tester, 'Confirm');

      final sent = api.confirmed!;
      expect((sent.firstName, sent.lastName, sent.mobile),
          ('Aarav', 'Mehta', '9xxxxx0101'));
      expect([
        for (final v in sent.vehicles)
          (v.id, v.parkingBasement, v.parkingNumber, v.cutoffTime, v.interiorDay)
      ], [
        ('v1', 'B2', '14', '07:00', 'Sunday'),
        ('v2', 'B3', '127', '06:30', null),
        ('v3', 'B1', '40', null, null),
      ]);
      expect(find.byType(OnboardingReviewScreen), findsNothing);
      expect(find.textContaining(RegExp(r'^Good (morning|afternoon|evening),$')), findsOneWidget);
    });

    testWidgets('a vehicle without its photo cannot continue (ONB-22)',
        (tester) async {
      await openAsCustomer(tester, confirmed: false, hasPhoto: false);
      await tester.enterText(find.byType(TextField).at(1), 'Mehta');
      await next(tester);
      await next(tester);
      expect(find.text('Vehicle 1 of 3'), findsOneWidget);
      await next(tester);
      expect(find.text('Add a photo of your car to continue.'), findsOneWidget);
      expect(find.text('Vehicle 1 of 3'), findsOneWidget);
    });

    testWidgets('a changed mobile number must be 10 digits', (tester) async {
      await openAsCustomer(tester, confirmed: false);
      await tester.enterText(find.byType(TextField).at(1), 'Mehta');
      await tester.enterText(find.byType(TextField).at(2), '98765');
      await next(tester);
      expect(find.text('Enter a 10-digit mobile number.'), findsOneWidget);
      await tester.enterText(find.byType(TextField).at(2), '9876543210');
      await next(tester);
      expect(find.text('Your society'), findsOneWidget);

      await next(tester, 'Back');
      expect(find.text('9876543210'), findsOneWidget);
    });

    testWidgets('a refusal from the API is shown and Home stays closed',
        (tester) async {
      final api = await openAsCustomer(tester, confirmed: false);
      await tester.enterText(find.byType(TextField).at(0), 'Fail');
      await tester.enterText(find.byType(TextField).at(1), 'Mehta');
      await next(tester);
      await next(tester);
      await next(tester);
      await tester.tap(find.text('B1'));
      await tester.enterText(find.byType(TextField), '9');
      await tester.tap(find.text('Choose a time'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('6:00 AM'));
      await tester.pumpAndSettle();
      await next(tester);
      await next(tester);
      await next(tester, 'Confirm');
      expect(find.text('Please check the details.'), findsOneWidget);
      expect(api.confirmed, isNull);
      expect(find.byType(OnboardingReviewScreen), findsOneWidget);

      // "Edit" goes back to the step.
      await tester.tap(find.text('Edit').first);
      await tester.pumpAndSettle();
      expect(find.text('Step 1 of 6'), findsOneWidget);
    });

    testWidgets('the customer can sign out of the review', (tester) async {
      await openAsCustomer(tester, confirmed: false);
      await tester.tap(find.byTooltip('Sign out'));
      await tester.pumpAndSettle();
      expect(find.byType(OnboardingReviewScreen), findsNothing);
      expect(find.text('Get started'), findsOneWidget);
      await tester.tap(find.text('Get started'));
      await tester.pumpAndSettle();
      expect(find.text('Continue'), findsOneWidget);
    });
  });

  test('cutoff times are every half hour of the day', () {
    expect(cutoffTimes, hasLength(48));
    expect(cutoffTimes.first, '00:00');
    expect(cutoffTimes[13], '06:30');
    expect(cutoffTimes.last, '23:30');
  });
}
