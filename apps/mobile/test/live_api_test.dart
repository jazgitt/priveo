// Calls a running API with the real Dio client and repositories.
// Skipped unless LIVE_API_URL is set, for example:
//   flutter test test/live_api_test.dart --dart-define=LIVE_API_URL=http://127.0.0.1:8000 \
//     --dart-define=LIVE_PASSWORD=...   (the same password for the three mock logins)
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/network/api_client.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/features/admin_quick/home/admin_home_data.dart';
import 'package:priveo/features/auth/data/auth_repository.dart';
import 'package:priveo/features/crew/home/crew_home_data.dart';
import 'package:priveo/features/customer/home/customer_home_data.dart';

const _url = String.fromEnvironment('LIVE_API_URL');
const _password = String.fromEnvironment('LIVE_PASSWORD');

void main() {
  group('live API', () {
    String? token;
    final dio = buildDio(
      baseUrl: _url,
      accessToken: () => token,
      refreshTokens: () async => false,
    );
    final auth = ApiAuthRepository(dio);

    Future<Session> signIn(String id) async {
      final s = await auth.login(id, _password);
      token = s.accessToken;
      return s;
    }

    test('wrong password gives the API message', () async {
      await expectLater(
        auth.login('priveopapa', 'definitely-wrong'),
        throwsA(isA<ApiFailure>().having(
            (e) => e.message, 'message', 'The ID or password is not correct.')),
      );
    });

    test('customer', () async {
      expect((await signIn('customer@priveo.test')).role, Role.customer);
      final h = await ApiCustomerHomeRepository(dio).fetch();
      expect(h.quickActions, hasLength(4));
    });

    test('crew', () async {
      expect((await signIn('9000000002')).role, Role.crew);
      final h = await ApiCrewHomeRepository(dio).fetch();
      expect(h.jobs, isNotEmpty);
    });

    test('admin', () async {
      expect((await signIn('priveopapa')).role, Role.admin);
      final h = await ApiAdminHomeRepository(dio).fetch();
      expect(h.payments, isNotEmpty);
    });

    test('a role cannot read another role home', () async {
      await signIn('customer@priveo.test');
      await expectLater(
        ApiAdminHomeRepository(dio).fetch(),
        throwsA(isA<ApiFailure>().having((e) => e.statusCode, 'status', 403)),
      );
    });
  }, skip: _url.isEmpty ? 'LIVE_API_URL not set' : false);
}
