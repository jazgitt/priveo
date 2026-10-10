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
/// the API's message.
class FakeAuthRepository implements AuthRepository {
  static const wrongMessage = 'The ID or password is not correct.';
  static const _accounts = {
    'customer@priveo.test': customerSession,
    '9000000002': crewSession,
    'priveopapa': adminSession,
  };

  int logoutCalls = 0;

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
  @override
  Future<CustomerHome> customerHome() async =>
      CustomerHome.fromJson(customerJson);

  @override
  Future<CrewHome> crewHome() async => CrewHome.fromJson(crewJson);

  @override
  Future<AdminHome> adminHome() async => AdminHome.fromJson(adminJson);

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

const customerJson = {
  'greeting_name': 'Aarav',
  'vehicle': {
    'registration': 'MH 12 AB 1234',
    'model': 'Hyundai Creta',
    'society': 'Green Meadows',
    'parking': 'B2-14',
  },
  'next_service': {
    'date': '2026-11-07',
    'service': 'Cleaning-External',
    'status': 'Scheduled',
  },
  'subscription_status': 'Active',
  'quick_actions': [
    {'key': 'skip_pause', 'label': 'Skip or Pause'},
    {'key': 'history', 'label': 'Service History'},
    {'key': 'feedback', 'label': 'Give Feedback'},
    {'key': 'report_issue', 'label': 'Report an Issue'},
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
  Brightness brightness = Brightness.light,
}) async {
  tester.platformDispatcher.platformBrightnessTestValue = brightness;
  addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);
  final container = ProviderContainer(overrides: [
    appConfigProvider.overrideWithValue(AppConfig.dev),
    sessionStoreProvider.overrideWithValue(store ?? MemorySessionStore()),
    authRepositoryProvider.overrideWithValue(auth ?? FakeAuthRepository()),
    apiProvider.overrideWithValue(FakePriveoApi()),
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
