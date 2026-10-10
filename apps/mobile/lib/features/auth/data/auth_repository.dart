import '../../../core/api/api.g.dart';
import '../../../core/auth/session.dart';
import '../../../core/network/api_failure.dart';

abstract class AuthRepository {
  /// What to ask for next: the password, or the code just emailed (AUTH-03).
  Future<StartResult> start(String loginId);

  /// Emails a customer a new code. Returns the seconds until the next resend.
  Future<int> sendCode(String email);

  /// Returns the one-time token that lets the customer set a password.
  Future<String> verifyCode(String email, String code);

  /// Sets the password after a correct code and signs the customer in.
  Future<Session> setPassword(String passwordToken, String password);

  Future<Session> login(String loginId, String password);
  Future<Session> refresh(String refreshToken);
  Future<void> logout();

  /// Ends every session of this login, on every device (ADM-ACC-14).
  Future<void> logoutAll();
}

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._api);

  final PriveoApi _api;

  @override
  Future<StartResult> start(String loginId) =>
      _api.start(StartRequest(loginId: loginId));

  @override
  Future<int> sendCode(String email) async =>
      (await _api.sendCode(CodeRequest(email: email))).resendInSeconds;

  @override
  Future<String> verifyCode(String email, String code) async =>
      (await _api.verifyCode(VerifyCodeRequest(email: email, code: code)))
          .passwordToken;

  @override
  Future<Session> setPassword(String passwordToken, String password) async =>
      Session.fromLogin(await _api.setPassword(SetPasswordRequest(
          passwordToken: passwordToken, password: password)));

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

  @override
  Future<void> logoutAll() => _api.logoutAll();
}
