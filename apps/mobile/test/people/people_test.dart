// The crew profile (CRW-PRF-01) and the customer's vehicle list and details
// (VEH-02, VEH-03, VEH-06, SUB-02).
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/people/data/people_repository.dart';
import 'package:priveo/features/people/routes.dart';
import 'package:priveo/l10n/app_localizations.dart';

import '../support/fakes.dart';

const _days = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

final profileJson = {
  'name': 'Raj Singh',
  'mobile': '9000000555',
  'society': 'Green Meadows',
  'role': 'Member',
  'working_hours': [
    for (final d in _days)
      {
        'day': d,
        'working': d != 'Sunday',
        'start': d != 'Sunday' ? '07:00' : '',
        'end': d != 'Sunday' ? '15:30' : '',
      },
  ],
};

class FakePeopleRepository implements PeopleRepository {
  FakePeopleRepository({this.failure});

  final ApiFailure? failure;

  @override
  Future<CrewProfile> crewProfile() async {
    if (failure != null) throw failure!;
    return CrewProfile.fromJson(profileJson);
  }
}

class _SignOutAuth extends FakeAuthRepository {}

Future<void> open(
  WidgetTester tester,
  String location, {
  PeopleRepository? people,
}) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final router = GoRouter(initialLocation: location, routes: routes);
  addTearDown(router.dispose);
  await tester.pumpWidget(ProviderScope(
    overrides: [
      sessionStoreProvider.overrideWithValue(MemorySessionStore()),
      authRepositoryProvider.overrideWithValue(_SignOutAuth()),
      apiProvider.overrideWithValue(FakePriveoApi()),
      peopleRepositoryProvider
          .overrideWithValue(people ?? FakePeopleRepository()),
    ],
    child: MaterialApp.router(
      theme: customerTheme,
      routerConfig: router,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
    ),
  ));
  await tester.pumpAndSettle();
}

void main() {
  group('crew profile', () {
    test('reads the API reply', () {
      final p = CrewProfile.fromJson(profileJson);
      expect(p.name, 'Raj Singh');
      expect(p.workingHours, hasLength(7));
      expect(p.workingHours.last.working, isFalse);
    });

    testWidgets('shows the profile, read only, with the hours',
        (tester) async {
      await open(tester, '/crew/profile');
      expect(find.text('Raj Singh'), findsOneWidget);
      expect(find.text('9000000555'), findsOneWidget);
      expect(find.text('Green Meadows'), findsOneWidget);
      expect(find.text('Member'), findsWidgets);
      expect(find.text('7:00 AM to 3:30 PM'), findsNWidgets(6));
      expect(find.text('Off'), findsOneWidget);
      // Nothing on the profile can be edited (CRW-PRF-03).
      expect(find.byType(TextField), findsNothing);
      expect(find.textContaining('set by Priveo'), findsOneWidget);
    });

    testWidgets('says plainly when the crew record is missing',
        (tester) async {
      await open(
        tester,
        '/crew/profile',
        people: FakePeopleRepository(
          failure: const ApiFailure(
              code: 'no_crew_record', message: 'x', statusCode: 404),
        ),
      );
      expect(find.text('Your details are not set up yet. Contact Priveo.'),
          findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('vehicles', () {
    testWidgets('lists every vehicle with its subscription status',
        (tester) async {
      await open(tester, '/customer/vehicles');
      expect(find.text('My vehicles'), findsOneWidget);
      expect(find.text('MH 12 AB 1234'), findsOneWidget);
      expect(find.text('Hyundai Creta'), findsOneWidget);
      expect(find.text('Number to be added'), findsOneWidget);
      expect(find.text('Active'), findsNWidgets(2));
      expect(find.text('No subscription'), findsOneWidget);
    });

    testWidgets('opens the details of a vehicle', (tester) async {
      await open(tester, '/customer/vehicles');
      await tester.tap(find.text('Hyundai Creta'));
      await tester.pumpAndSettle();
      expect(find.text('Vehicle details'), findsOneWidget);
      expect(find.text('B2-14'), findsOneWidget);
      expect(find.text('Green Meadows'), findsOneWidget);
      expect(find.text('₹1,299'), findsOneWidget);
      expect(find.text('7:00 AM'), findsOneWidget);
      expect(find.text('Friday'), findsOneWidget);
    });

    testWidgets('a vehicle without a subscription has no plan details',
        (tester) async {
      await open(tester, '/customer/vehicles/v3');
      expect(find.text('DL 3 CAB 1234'), findsOneWidget);
      expect(find.text('No subscription'), findsOneWidget);
      expect(find.text('Monthly amount'), findsNothing);
    });

    testWidgets('a vehicle that is not on the account is said so',
        (tester) async {
      await open(tester, '/customer/vehicles/nope');
      expect(find.text('This vehicle is not on your account.'), findsOneWidget);
    });
  });
}
