import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../changes_money/data/money_repository.dart' show newIdempotencyKey;

/// The outcome of a cutoff change for one date (CAL-08, CAL-07).
class CutoffChangeResult {
  const CutoffChangeResult({required this.status});

  /// `Applied`, or `Requested` when the schedule is frozen.
  final String status;

  bool get requested => status == 'Requested';
}

/// The result of editing the default cutoff time or interior day (SUB-08).
class PreferencesResult {
  const PreferencesResult({
    required this.cutoffTime,
    required this.interiorDay,
    required this.appliesFrom,
    required this.frozenDaysUnchanged,
  });

  final String? cutoffTime;
  final String? interiorDay;
  final DateTime appliesFrom;
  final int frozenDaysUnchanged;
}

String _ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// What the calendar day card does to the schedule. Tests use a fake.
abstract class CalendarActions {
  /// Returns the skip's ID.
  Future<String> skip(String vehicleId, DateTime date);
  Future<void> unskip(String vehicleId, String skipId);
  Future<CutoffChangeResult> changeCutoff(
    String vehicleId,
    DateTime date,
    String cutoff,
  );
  Future<PreferencesResult> updatePreferences(
    String vehicleId, {
    String? cutoffTime,
    String? interiorDay,
  });
}

class DioCalendarActions implements CalendarActions {
  DioCalendarActions(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>?> _send(
    Future<Response<dynamic>> Function() f,
  ) async {
    try {
      final r = await f();
      return r.data is Map<String, dynamic>
          ? r.data as Map<String, dynamic>
          : null;
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  Options _key() => Options(headers: {'Idempotency-Key': newIdempotencyKey()});

  @override
  Future<String> skip(String vehicleId, DateTime date) async {
    final j = await _send(
      () => _dio.post<dynamic>(
        '/v1/customer/vehicles/$vehicleId/skips',
        data: {'date': _ymd(date)},
        options: _key(),
      ),
    );
    return j!['id'] as String;
  }

  @override
  Future<void> unskip(String vehicleId, String skipId) async {
    await _send(
      () => _dio.delete<dynamic>(
        '/v1/customer/vehicles/$vehicleId/skips/$skipId',
      ),
    );
  }

  @override
  Future<CutoffChangeResult> changeCutoff(
    String vehicleId,
    DateTime date,
    String cutoff,
  ) async {
    final j = await _send(
      () => _dio.post<dynamic>(
        '/v1/customer/vehicles/$vehicleId/cutoff-changes',
        data: {'date': _ymd(date), 'cutoff_time': cutoff},
        options: _key(),
      ),
    );
    return CutoffChangeResult(status: j!['status'] as String);
  }

  @override
  Future<PreferencesResult> updatePreferences(
    String vehicleId, {
    String? cutoffTime,
    String? interiorDay,
  }) async {
    final j = await _send(
      () => _dio.patch<dynamic>(
        '/v1/customer/vehicles/$vehicleId/preferences',
        data: {'cutoff_time': ?cutoffTime, 'interior_day': ?interiorDay},
      ),
    );
    return PreferencesResult(
      cutoffTime: j!['cutoff_time'] as String?,
      interiorDay: j['interior_day'] as String?,
      appliesFrom: DateTime.parse(j['applies_from'] as String),
      frozenDaysUnchanged: j['frozen_days_unchanged'] as int,
    );
  }
}

final calendarActionsProvider = Provider<CalendarActions>(
  (ref) => DioCalendarActions(ref.watch(dioProvider)),
);
