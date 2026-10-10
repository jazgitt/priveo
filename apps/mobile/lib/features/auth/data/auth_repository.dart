import '../../../core/api/api.g.dart';
import '../../../core/auth/session.dart';
import '../../../core/network/api_failure.dart';

abstract class AuthRepository {
  Future<Session> login(String loginId, String password);
  Future<Session> refresh(String refreshToken);
  Future<void> logout();
}

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._api);

  final PriveoApi _api;

  @override
  Future<Session> login(String loginId, String password) async =>
      Session.fromLogin(await _api
          .login(LoginRequest(loginId: loginId, password: password)));

  @override
  Future<Session> refresh(String refreshToken) async => Session.fromLogin(
      await _api.refresh(RefreshRequest(refreshToken: refreshToken)));

  @override
  Future<void> logout() async {
    try {
      await _api.logout();
    } on ApiFailure {
      // Signing out always succeeds on the phone.
    }
  }
}
