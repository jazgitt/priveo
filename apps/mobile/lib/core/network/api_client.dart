import 'package:dio/dio.dart';

/// Builds the Dio client: adds the bearer token and, on a 401, gets new
/// tokens once and repeats the call.
Dio buildDio({
  required String baseUrl,
  required String? Function() accessToken,
  required Future<bool> Function() refreshTokens,
}) {
  final dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 20),
    headers: {'Accept': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) {
      final token = accessToken();
      if (options.extra['noAuth'] != true && token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      handler.next(options);
    },
    onError: (e, handler) async {
      final req = e.requestOptions;
      final canRetry = e.response?.statusCode == 401 &&
          req.extra['noAuth'] != true &&
          req.extra['retried'] != true;
      if (!canRetry) return handler.next(e);
      if (await refreshTokens()) {
        req.extra['retried'] = true;
        req.headers['Authorization'] = 'Bearer ${accessToken()}';
        try {
          return handler.resolve(await dio.fetch<dynamic>(req));
        } on DioException catch (retryError) {
          return handler.next(retryError);
        }
      }
      handler.next(e);
    },
  ));
  return dio;
}
