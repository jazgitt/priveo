import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';

DioException _reply(int status, Object? data) {
  final options = RequestOptions(path: '/x');
  return DioException(
    requestOptions: options,
    type: DioExceptionType.badResponse,
    response: Response(requestOptions: options, statusCode: status, data: data),
  );
}

void main() {
  test('the API error envelope gives the code, message and status', () {
    final f = ApiFailure.fromDio(
        _reply(422, {'code': 'validation_failed', 'message': 'Check it.'}));
    expect(f.code, 'validation_failed');
    expect(f.message, 'Check it.');
    expect(f.statusCode, 422);
    expect(f.isNetwork, isFalse);
  });

  test('a host 413 page is "too large to send", not a lost connection', () {
    final f = ApiFailure.fromDio(_reply(413, 'Request Entity Too Large'));
    expect(f.code, 'too_large');
    expect(f.message, 'This file is too large to send.');
    expect(f.statusCode, 413);
    expect(f.isNetwork, isFalse);
  });

  test('another reply without the envelope keeps its status and is not offline', () {
    final f = ApiFailure.fromDio(_reply(502, '<html>Bad gateway</html>'));
    expect(f.message, isNull);
    expect(f.statusCode, 502);
    expect(f.isNetwork, isFalse);
  });

  test('no reply at all is a lost connection', () {
    final f = ApiFailure.fromDio(DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.connectionError));
    expect(f.isNetwork, isTrue);
    expect(const ApiFailure().isNetwork, isTrue);
  });
}
