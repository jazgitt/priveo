import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

typedef AdminRow = Map<String, dynamic>;

class AdminActionsRepository {
  AdminActionsRepository(this.dio);
  final Dio dio;

  Future<T> _send<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  Future<List<AdminRow>> list(String path, [AdminRow? query]) => _send(
    () async => [
      for (final item in (await dio.get<List<dynamic>>(
        path,
        queryParameters: query,
      )).data!)
        Map<String, dynamic>.from(item as Map),
    ],
  );
  Future<AdminRow> detail(String path) =>
      _send(() async => (await dio.get<AdminRow>(path)).data!);
  Future<void> post(String path, AdminRow body) => _send(() async {
    await dio.post<dynamic>(path, data: body);
  });
  Future<void> remove(String path) => _send(() async {
    await dio.delete<dynamic>(path);
  });
}

final adminActionsRepositoryProvider = Provider(
  (ref) => AdminActionsRepository(ref.watch(dioProvider)),
);

String adminDate(DateTime date) =>
    '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
