import 'package:dio/dio.dart';

/// An error from the API, using the server's error envelope.
/// [message] and [statusCode] are both null when the server could not be
/// reached at all.
class ApiFailure implements Exception {
  const ApiFailure({this.code = 'network', this.message, this.statusCode});

  final String code;
  final String? message;
  final int? statusCode;

  /// No answer came back. A reply without our error envelope (for example a
  /// host's 413 "too large" page) is an answer, not a lost connection.
  bool get isNetwork => message == null && statusCode == null;

  factory ApiFailure.fromDio(DioException e) {
    final data = e.response?.data;
    final status = e.response?.statusCode;
    if (data is Map && data['message'] is String) {
      return ApiFailure(
        code: (data['code'] as String?) ?? 'error',
        message: data['message'] as String,
        statusCode: status,
      );
    }
    if (status == 413) {
      return const ApiFailure(
          code: 'too_large',
          message: 'This file is too large to send.',
          statusCode: 413);
    }
    return ApiFailure(statusCode: status);
  }

  @override
  String toString() => 'ApiFailure($code, $message)';
}
