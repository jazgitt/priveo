import '../../../core/network/read_refresh.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import 'admin_quick_models.dart';

/// Every admin read and write the quick actions need. A fake implements this
/// in tests.
abstract class AdminQuickRepository {
  Future<QuickHome> home();
  Future<List<QuickComplaint>> complaints({String? status, String? category});
  Future<QuickComplaint> complaint(String id);
  Future<QuickComplaint> setStatus(String id, String status, String note);
  Future<QuickComplaint> addNote(String id, String note);
  Future<List<QuickFeedback>> feedback({int? rating});
  Future<QuickRatings> ratings();
  Future<List<QuickJob>> needsScheduling({String? societyId});
  Future<DaySchedule> day(DateTime date, {String? societyId});
  Future<List<DayCapacity>> capacity(
    String societyId,
    DateTime start, {
    int days = 7,
  });
}

String _apiDate(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

class ApiAdminQuickRepository implements AdminQuickRepository {
  ApiAdminQuickRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() send) async {
    try {
      return await send();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  Future<Map<String, dynamic>> _getMap(
    String path, [
    Map<String, dynamic>? query,
  ]) => _call(
    () async => (await _dio.get<Map<String, dynamic>>(
      path,
      queryParameters: query,
    )).data!,
  );

  Future<List<Map<String, dynamic>>> _getList(
    String path, [
    Map<String, dynamic>? query,
  ]) => _call(() async {
    final r = await _dio.get<List<dynamic>>(path, queryParameters: query);
    return [for (final e in r.data!) e as Map<String, dynamic>];
  });

  @override
  Future<QuickHome> home() async =>
      QuickHome.fromJson(await _getMap('/v1/admin/home'));

  @override
  Future<List<QuickComplaint>> complaints({
    String? status,
    String? category,
  }) async => [
    for (final j in await _getList('/v1/admin/complaints', {
      'status': ?status,
      'category': ?category,
    }))
      QuickComplaint.fromJson(j),
  ];

  @override
  Future<QuickComplaint> complaint(String id) async =>
      QuickComplaint.fromJson(await _getMap('/v1/admin/complaints/$id'));

  Future<QuickComplaint> _post(String path, Map<String, dynamic> body) => _call(
    () async => QuickComplaint.fromJson(
      (await _dio.post<Map<String, dynamic>>(path, data: body)).data!,
    ),
  );

  @override
  Future<QuickComplaint> setStatus(String id, String status, String note) =>
      _post('/v1/admin/complaints/$id/status', {
        'status': status,
        'note': note,
      });

  @override
  Future<QuickComplaint> addNote(String id, String note) =>
      _post('/v1/admin/complaints/$id/notes', {'note': note});

  @override
  Future<List<QuickFeedback>> feedback({int? rating}) async => [
    for (final j in await _getList('/v1/admin/feedback', {'rating': ?rating}))
      QuickFeedback.fromJson(j),
  ];

  @override
  Future<QuickRatings> ratings() async =>
      QuickRatings.fromJson(await _getMap('/v1/admin/ratings'));

  @override
  Future<List<QuickJob>> needsScheduling({String? societyId}) async {
    final j = await _getMap('/v1/admin/scheduling/needs-scheduling', {
      'society_id': ?societyId,
    });
    return [
      for (final e in (j['jobs'] as List))
        QuickJob.fromJson(e as Map<String, dynamic>),
    ];
  }

  @override
  Future<DaySchedule> day(DateTime date, {String? societyId}) async =>
      DaySchedule.fromJson(
        await _getMap('/v1/admin/schedule/day', {
          'date': _apiDate(date),
          'society_id': ?societyId,
        }),
      );

  @override
  Future<List<DayCapacity>> capacity(
    String societyId,
    DateTime start, {
    int days = 7,
  }) async => [
    for (final j in await _getList('/v1/admin/scheduling/capacity', {
      'society_id': societyId,
      'start_date': _apiDate(start),
      'days': days,
    }))
      DayCapacity.fromJson(j),
  ];
}

final adminQuickRepositoryProvider = Provider<AdminQuickRepository>(
  (ref) => ApiAdminQuickRepository((ref.watch(readRefreshProvider), ref.watch(dioProvider)).$2),
);
