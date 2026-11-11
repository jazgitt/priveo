// Calls a running API with the real Dio client and the generated API client.
// Skipped unless LIVE_API_URL is set, for example:
//   flutter test test/live_api_test.dart --dart-define=LIVE_API_URL=http://127.0.0.1:8000 \
//     --dart-define=LIVE_PASSWORD=...
// LIVE_PASSWORD is used for all three mock logins. When they differ, set
// LIVE_CUSTOMER_PASSWORD, LIVE_CREW_PASSWORD and LIVE_ADMIN_PASSWORD.
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/api/api.g.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/network/api_client.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/features/auth/data/auth_repository.dart';

const _url = String.fromEnvironment('LIVE_API_URL');
const _password = String.fromEnvironment('LIVE_PASSWORD');
// The admin's ID is environment configuration (ADMIN_LOGIN_ID), passed in.
const _adminId =
    String.fromEnvironment('LIVE_ADMIN_ID', defaultValue: 'test-admin-id');
const _passwords = {
  '9000000001':
      String.fromEnvironment('LIVE_CUSTOMER_PASSWORD', defaultValue: _password),
  '9000000002':
      String.fromEnvironment('LIVE_CREW_PASSWORD', defaultValue: _password),
  _adminId:
      String.fromEnvironment('LIVE_ADMIN_PASSWORD', defaultValue: _password),
};

const _roles = {
  '9000000001': 'customer',
  '9000000002': 'crew',
  _adminId: 'admin',
};

void main() {
  group('live API', () {
    String? token;
    final dio = buildDio(
      baseUrl: _url,
      accessToken: () => token,
      refreshTokens: () async => false,
    );
    final api = PriveoApi(dio);
    final auth = ApiAuthRepository(api);

    Future<Session> signIn(String id) async {
      final s = await auth.login(id, _passwords[id]!, _roles[id]!);
      token = s.accessToken;
      return s;
    }

    test('wrong password gives the API message', () async {
      await expectLater(
        auth.login(_adminId, 'definitely-wrong', 'admin'),
        throwsA(isA<ApiFailure>().having(
            (e) => e.message, 'message', 'The ID or password is not correct.')),
      );
    });

    test('customer', () async {
      expect((await signIn('9000000001')).role, Role.customer);
      final h = await api.customerHome();
      expect(h.quickActions, hasLength(4));
    });

    test('crew', () async {
      expect((await signIn('9000000002')).role, Role.crew);
    });

    test('admin', () async {
      expect((await signIn(_adminId)).role, Role.admin);
      final h = await api.adminHome();
      expect(h.paymentsToConfirm, isNotEmpty);
    });

    test('a role cannot read another role home', () async {
      await signIn('9000000001');
      await expectLater(
        api.adminHome(),
        throwsA(isA<ApiFailure>().having((e) => e.statusCode, 'status', 403)),
      );
    });
  }, skip: _url.isEmpty ? 'LIVE_API_URL not set' : false);
}
