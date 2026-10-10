import 'package:dio/dio.dart';

import '../../../core/auth/session.dart';
import '../../../core/network/api_failure.dart';

abstract class AuthRepository {
  Future<Session> login(String loginId, String password);
  Future<Session> refresh(String refreshToken);
  Future<void> logout();
}

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._dio);

  final Dio _dio;

  /// Auth calls must not carry or retry with the bearer token.
  static final _noAuth = Options(extra: {'noAuth': true});

  @override
  Future<Session> login(String loginId, String password) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/v1/auth/login',
        data: {'login_id': loginId, 'password': password},
        options: _noAuth,
      );
      return Session.fromLoginJson(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<Session> refresh(String refreshToken) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: _noAuth,
      );
      return Session.fromLoginJson(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<void> logout() async {
    try {
      await _dio.post<void>('/v1/auth/logout');
    } on DioException {
      // Signing out always succeeds on the phone.
    }
  }
}
