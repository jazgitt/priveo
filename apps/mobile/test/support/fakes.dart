import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/app.dart';
import 'package:priveo/core/api/api.g.dart' hide AppConfig;
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/config/app_config.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/features/auth/data/auth_repository.dart';

const customerSession = Session(
    role: Role.customer,
    displayName: 'Aarav Mehta',
    accessToken: 'a-customer',
    refreshToken: 'r-customer');
const crewSession = Session(
    role: Role.crew,
    displayName: 'Ravi Kumar',
    accessToken: 'a-crew',
    refreshToken: 'r-crew');
const adminSession = Session(
    role: Role.admin,
    displayName: 'Priveo Admin',
    accessToken: 'a-admin',
    refreshToken: 'r-admin');

/// Accepts the password "secret" for the three demo IDs. Anything else gets
/// the API's message. [newCustomer] has no password yet: it gets the code
/// [code], and then signs in as the customer.
class FakeAuthRepository implements AuthRepository {
  static const wrongMessage = 'The ID or password is not correct.';
  static const notRegistered = 'This email is not registered. Contact Priveo.';
  static const wrongCode = 'The code is not correct.';
  static const newCustomer = 'new@priveo.test';
  static const code = '246810';
  static const _accounts = {
    'customer@priveo.test': customerSession,
    '9000000002': crewSession,
    'priveopapa': adminSession,
  };

  int logoutCalls = 0;
  int codesSent = 0;
  String? passwordSet;

  @override
  Future<StartResult> start(String loginId) async {
    if (loginId == newCustomer) {
      codesSent++;
      return const StartResult(next: 'code', resendInSeconds: 30);
    }
    if (loginId.contains('@') && !_accounts.containsKey(loginId)) {
      throw const ApiFailure(
          code: 'email_not_registered', message: notRegistered, statusCode: 404);
    }
    return const StartResult(next: 'password', resendInSeconds: 0);
  }

  @override
  Future<int> sendCode(String email) async {
    codesSent++;
    return 30;
  }

  @override
  Future<String> verifyCode(String email, String code) async {
    if (code != FakeAuthRepository.code) {
      throw const ApiFailure(
          code: 'invalid_code', message: wrongCode, statusCode: 400);
    }
    return 'password-token';
  }

  @override
  Future<Session> setPassword(String passwordToken, String password) async {
    passwordSet = password;
    return customerSession;
  }

  @override
  Future<Session> login(String loginId, String password) async {
    final s = _accounts[loginId];
    if (s == null || password != 'secret') {
      throw const ApiFailure(
          code: 'invalid_credentials', message: wrongMessage, statusCode: 401);
    }
    return s;
  }

  @override
  Future<Session> refresh(String refreshToken) async =>
      throw const ApiFailure();

  @override
  Future<void> logout() async => logoutCalls++;

  int logoutAllCalls = 0;

  @override
  Future<void> logoutAll() async => logoutAllCalls++;
}

/// Serves the three homes from the JSON below. Other calls are not used
/// by the screens under test.
class FakePriveoApi implements PriveoApi {
  FakePriveoApi({this.onboardingConfirmed = true});

  /// False for a customer who has not reviewed their details yet (ONB-25).
  bool onboardingConfirmed;
  OnboardingAnswers? confirmed;

  @override
  Future<CustomerHome> customerHome() async => CustomerHome.fromJson(
      {...customerJson, 'onboarding_confirmed': onboardingConfirmed});

  @override
  Future<Onboarding> onboarding() async => Onboarding.fromJson(onboardingJson);

  @override
  Future<void> confirmOnboarding(OnboardingAnswers body) async {
    if (body.firstName == 'Fail') {
      throw const ApiFailure(
          code: 'validation_failed',
          message: 'Please check the details.',
          statusCode: 422);
    }
    confirmed = body;
    onboardingConfirmed = true;
  }

  @override
  Future<CrewHome> crewHome() async => CrewHome.fromJson(crewJson);

  @override
  Future<AdminHome> adminHome() async => AdminHome.fromJson(adminJson);

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

const customerJson = {
  'greeting_name': 'Aarav',
  'onboarding_confirmed': true,
  'vehicles': [
    {
      'id': 'v1',
      'registration': 'MH 12 AB 1234',
      'model': 'Hyundai Creta',
      'society': 'Green Meadows',
      'parking': 'B2-14',
      'subscription_status': 'Active',
      'monthly_price_rupees': 1299,
      'cutoff_time': '07:00',
      'interior_day': 'Friday',
      'next_service': {
        'date': '2026-11-07',
        'service': 'Cleaning-External',
        'status': 'Scheduled',
      },
    },
    {
      'id': 'v2',
      'registration': '',
      'model': 'Maruti Swift',
      'society': 'Green Meadows',
      'parking': '',
      'subscription_status': 'Active',
      'monthly_price_rupees': 999,
      'cutoff_time': '06:30',
      'interior_day': null,
      'next_service': null,
    },
    {
      'id': 'v3',
      'registration': 'DL 3 CAB 1234',
      'model': 'Tata Punch',
      'society': 'Green Meadows',
      'parking': 'B1-40',
      'subscription_status': null,
      'monthly_price_rupees': null,
      'cutoff_time': null,
      'interior_day': null,
      'next_service': null,
    },
  ],
  'quick_actions': [
    {'key': 'skip_pause', 'label': 'Skip or Pause'},
    {'key': 'history', 'label': 'Service History'},
    {'key': 'feedback', 'label': 'Give Feedback'},
    {'key': 'report_issue', 'label': 'Report an Issue'},
  ],
};

/// A migrated customer with gaps: no last name, a masked mobile number, a
/// car with no parking or cutoff time, and a car with no subscription.
const onboardingJson = {
  'confirmed': false,
  'first_name': 'Aarav',
  'last_name': '',
  'email': 'aarav@gmale.com',
  'mobile': '9xxxxx0101',
  'society': 'Green Meadows',
  'flat': 'A-101',
  'vehicles': [
    {
      'id': 'v1',
      'registration': 'MH 12 AB 1234',
      'model': 'Hyundai Creta',
      'parking_basement': 'B2',
      'parking_number': '14',
      'has_subscription': true,
      'plan_name': null,
      'monthly_price_rupees': 1299,
      'cutoff_time': '07:00',
      'asks_interior_day': true,
      'interior_day': 'Friday',
    },
    {
      'id': 'v2',
      'registration': '',
      'model': 'Maruti Swift',
      'parking_basement': '',
      'parking_number': '',
      'has_subscription': true,
      'plan_name': null,
      'monthly_price_rupees': 999,
      'cutoff_time': null,
      'asks_interior_day': false,
      'interior_day': null,
    },
    {
      'id': 'v3',
      'registration': 'DL 3 CAB 1234',
      'model': 'Tata Punch',
      'parking_basement': 'B1',
      'parking_number': '40',
      'has_subscription': false,
      'plan_name': null,
      'monthly_price_rupees': null,
      'cutoff_time': null,
      'asks_interior_day': false,
      'interior_day': null,
    },
  ],
};

const crewJson = {
  'date': '2026-11-07',
  'society': 'Green Meadows',
  'total': 2,
  'done': 1,
  'left': 1,
  'jobs': [
    {
      'id': 'j1',
      'time': '07:00',
      'vehicle': 'MH 12 AB 1234',
      'parking': 'B2-14',
      'service': 'Cleaning-External',
      'status': 'Done',
    },
    {
      'id': 'j2',
      'time': '07:20',
      'vehicle': 'MH 12 CD 5678',
      'parking': 'B2-15',
      'service': 'Cleaning-Internal',
      'status': 'Pending',
    },
  ],
};

const adminJson = {
  'alert_count': 3,
  'needs_scheduling_count': 2,
  'payments_to_confirm': [
    {
      'id': 'p1',
      'customer_label': 'Flat A-101',
      'amount_rupees': 1499,
      'reference': 'UPI 4021',
    },
  ],
};

/// Starts the real app with fake data sources.
Future<ProviderContainer> pumpApp(
  WidgetTester tester, {
  SessionStore? store,
  FakeAuthRepository? auth,
  FakePriveoApi? api,
  Brightness brightness = Brightness.light,
}) async {
  tester.platformDispatcher.platformBrightnessTestValue = brightness;
  addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);
  final container = ProviderContainer(overrides: [
    appConfigProvider.overrideWithValue(AppConfig.dev),
    sessionStoreProvider.overrideWithValue(store ?? MemorySessionStore()),
    authRepositoryProvider.overrideWithValue(auth ?? FakeAuthRepository()),
    apiProvider.overrideWithValue(api ?? FakePriveoApi()),
  ]);
  addTearDown(container.dispose);
  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const PriveoApp(),
  ));
  return container;
}

/// Plays the splash (about 2 seconds) and lets navigation finish.
Future<void> passSplash(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 3));
  await tester.pumpAndSettle();
}
