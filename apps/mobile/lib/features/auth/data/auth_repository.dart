import '../../../core/api/api.g.dart';
import '../../../core/auth/session.dart';
import '../../../core/network/api_failure.dart';

abstract class AuthRepository {
  /// Emails a customer a code to the email on file ("Forgot MPIN", AUTH-16).
  /// Returns the seconds until the next resend.
  Future<int> sendCode(String mobile);

  /// Returns the one-time token that lets the customer set a new MPIN.
  Future<String> verifyCode(String mobile, String code);

  /// Sets the MPIN after a correct code and signs the customer in.
  Future<Session> setMpin(String mpinToken, String mpin);

  /// [role] is 'customer', 'crew' or 'admin': a customer and a crew member can
  /// have the same mobile number, so the sign-in says which one it is.
  Future<Session> login(String loginId, String password, String role);
  Future<Session> refresh(String refreshToken);
  Future<void> logout();

  /// Ends every session of this login, on every device (ADM-ACC-14).
  Future<void> logoutAll();
}

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._api);

  final PriveoApi _api;

  @override
  Future<int> sendCode(String mobile) async =>
      (await _api.sendCode(CodeRequest(mobile: mobile))).resendInSeconds;

  @override
  Future<String> verifyCode(String mobile, String code) async =>
      (await _api.verifyCode(
        VerifyCodeRequest(mobile: mobile, code: code),
      )).mpinToken;

  @override
  Future<Session> setMpin(String mpinToken, String mpin) async =>
      Session.fromLogin(
        await _api.setMpin(SetMpinRequest(mpinToken: mpinToken, mpin: mpin)),
      );

  @override
  Future<Session> login(String loginId, String password, String role) async =>
      Session.fromLogin(
        await _api.login(
          LoginRequest(loginId: loginId, password: password, role: role),
        ),
      );

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
