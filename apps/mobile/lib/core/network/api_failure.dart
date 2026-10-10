import 'package:dio/dio.dart';

/// An error from the API, using the server's error envelope.
/// [message] is null when the server could not be reached.
class ApiFailure implements Exception {
  const ApiFailure({this.code = 'network', this.message, this.statusCode});

  final String code;
  final String? message;
  final int? statusCode;

  bool get isNetwork => message == null;

  factory ApiFailure.fromDio(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['message'] is String) {
      return ApiFailure(
        code: (data['code'] as String?) ?? 'error',
        message: data['message'] as String,
        statusCode: e.response?.statusCode,
      );
    }
    return ApiFailure(statusCode: e.response?.statusCode);
  }

  @override
  String toString() => 'ApiFailure($code, $message)';
}
