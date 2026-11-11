import 'package:priveo/features/customer/account/account_data.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/app.dart';
import 'package:priveo/core/api/api.g.dart' hide AppConfig;
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/config/app_config.dart';
import 'package:priveo/core/features/feature_flags.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/features/admin_quick/data/admin_quick_models.dart';
import 'package:priveo/features/admin_quick/data/admin_quick_repository.dart';
import 'package:priveo/features/auth/data/auth_repository.dart';
import 'package:priveo/features/crew/crew_providers.dart';
import 'package:priveo/features/crew/upload/upload_queue.dart';

import '../crew/support.dart' show FakeCrewBackend;

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

/// Accepts the password "secret" (a customer: the MPIN [mpin]) for the three demo IDs: a customer and a crew
/// member by mobile number, an admin by user ID. A customer who forgot the MPIN
/// gets the code [code] at the email on file, then sets a new MPIN and signs in.
class FakeAuthRepository implements AuthRepository {
  static const wrongMessage = 'The ID or password is not correct.';
  static const notRegistered =
      'This mobile number is not registered. Contact Priveo.';
  static const noEmail =
      'No email is saved for this number. Ask Priveo to reset your MPIN.';
  static const wrongCode = 'The code is not correct.';
  static const customerId = '9000000001';
  static const crewId = '9000000002';
  static const unknownMobile = '9111111111';
  static const noEmailMobile = '9000000004';
  static const code = '246810';
  // A customer's MPIN is 6 digits; crew and admin use the password "secret".
  static const mpin = '482915';
  static const _accounts = {
    'customer:9000000001': customerSession,
    'crew:9000000002': crewSession,
    'admin:test-admin-id': adminSession,
  };

  int logoutCalls = 0;
  int codesSent = 0;
  String? mpinSet;
  String? lastRole;

  @override
  Future<int> sendCode(String mobile) async {
    if (mobile == unknownMobile) {
      throw const ApiFailure(
        code: 'mobile_not_registered',
        message: notRegistered,
        statusCode: 404,
      );
    }
    if (mobile == noEmailMobile) {
      throw const ApiFailure(
        code: 'no_email',
        message: noEmail,
        statusCode: 409,
      );
    }
    codesSent++;
    return 30;
  }

  @override
  Future<String> verifyCode(String mobile, String code) async {
    if (code != FakeAuthRepository.code) {
      throw const ApiFailure(
          code: 'invalid_code', message: wrongCode, statusCode: 400);
    }
    return 'mpin-token';
  }

  @override
  Future<Session> setMpin(String mpinToken, String mpin) async {
    mpinSet = mpin;
    return customerSession;
  }

  @override
  Future<Session> login(String loginId, String password, String role) async {
    lastRole = role;
    final s = _accounts['$role:$loginId'];
    if (s == null || password != (role == 'customer' ? mpin : 'secret')) {
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
      'plan_name': 'Daily Premium',
      'payment_status': 'Due',
      'status_message': 'Due in 3 days',
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

/// The admin home reads its own endpoint. Everything else is not used by the
/// app tests, so it goes to a Dio with no server.
class FakeAdminQuickHome extends ApiAdminQuickRepository {
  FakeAdminQuickHome() : super(Dio());

  @override
  Future<QuickHome> home() async => QuickHome.fromJson(adminJson);
}

/// Starts the real app with fake data sources.
/// The customer's account calls with one thing: whether each vehicle has its
/// photo (ONB-22). Everything else answers with nothing.
class PhotoAccount implements AccountRepository {
  PhotoAccount({this.hasPhoto = true});

  bool hasPhoto;

  @override
  Future<VehicleAccountDto> vehicleAccount(String vehicleId) async =>
      VehicleAccountDto(
        id: vehicleId,
        parkingBasement: '',
        parkingNumber: '',
        photoUrl: hasPhoto ? 'https://media.test/car.jpg' : null,
        rcStatus: 'Not uploaded',
      );

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName}');
}

Future<ProviderContainer> pumpApp(
  WidgetTester tester, {
  AccountRepository? account,
  SessionStore? store,
  FakeAuthRepository? auth,
  FakePriveoApi? api,
  Brightness brightness = Brightness.light,
  List<Override> overrides = const [],
}) async {
  final crewBackend = FakeCrewBackend();
  final uploadQueue = UploadQueue(api: crewBackend,
      store: MemoryUploadQueueStore(), retryAfter: Duration.zero);
  addTearDown(uploadQueue.dispose);
  tester.platformDispatcher.platformBrightnessTestValue = brightness;
  addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);
  // No automatic retries: a tab kept alive whose fake route fails would leave
  // a retry timer pending when the test ends.
  final container = ProviderContainer(retry: (_, _) => null, overrides: [
    readRefreshProvider.overrideWith((ref) => const Stream<int>.empty()),
    appConfigProvider.overrideWithValue(AppConfig.test),
    sessionStoreProvider.overrideWithValue(store ?? MemorySessionStore()),
    authRepositoryProvider.overrideWithValue(auth ?? FakeAuthRepository()),
    apiProvider.overrideWithValue(api ?? FakePriveoApi()),
    accountRepositoryProvider.overrideWithValue(account ?? PhotoAccount()),
    adminQuickRepositoryProvider.overrideWithValue(FakeAdminQuickHome()),
    // The crew home reads its own endpoints and starts the upload queue. A
    // test has no network, no SQLite and no connectivity plugin.
    crewRepositoryProvider.overrideWithValue(crewBackend),
    uploadApiProvider.overrideWithValue(crewBackend),
    uploadQueueProvider.overrideWithValue(uploadQueue),
    uploadQueueStoreProvider.overrideWithValue(MemoryUploadQueueStore()),
    onlineEventsProvider.overrideWithValue(null),
    // The feature flags read the server and secure storage. A test has neither,
    // and a real request leaves a timer pending when the test ends. Every
    // feature is on, as before the first answer.
    featureFlagFetchProvider.overrideWithValue((role, etag) async => null),
    featureFlagStoreProvider.overrideWithValue(_NoFeatureFlagStore()),
    ...overrides,
  ]);
  addTearDown(container.dispose);
  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const PriveoApp(),
  ));
  return container;
}

class _NoFeatureFlagStore implements FeatureFlagStore {
  @override
  Future<FeatureFlags?> read(Role role) async => null;
  @override
  Future<void> write(Role role, FeatureFlags flags) async {}
}

/// Plays the splash (about 2 seconds) and lets navigation finish.
Future<void> passSplash(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 3));
  await tester.pumpAndSettle();
  // The welcome buttons are on the splash (AUTH-01); Get started opens the email step.
  final start = find.text('Get started');
  if (start.evaluate().isNotEmpty) {
    await tester.tap(start);
    await tester.pumpAndSettle();
  }
}
