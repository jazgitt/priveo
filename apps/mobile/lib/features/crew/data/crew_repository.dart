import 'dart:io';

import 'package:dio/dio.dart';

import '../../../core/network/api_failure.dart';
import 'crew_models.dart';
import 'manager_models.dart';

/// `yyyy-mm-dd`, as the API reads dates.
String apiDate(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-'
    '${d.day.toString().padLeft(2, '0')}';

/// Reads and changes the crew member's jobs. Screens test against fakes.
abstract class CrewRepository {
  /// The cards for [date], or every card when [all] is true (CRW-SCH-06).
  Future<CrewVisitList> visits({DateTime? date, bool all = false});
  Future<CrewJobDetail> job(String jobId);
  Future<CrewJobDetail> start(String jobId);
  Future<CrewJobDetail> setChecked(String jobId, String itemId, bool checked);
  Future<CrewJobDetail> complete(String jobId);
  Future<CrewJobDetail> couldNotComplete(String jobId,
      {required String reasonKey, String note = '', String? uploadId});
  Future<List<CrewReason>> reasons();
  Future<CrewProfileInfo> profile();
  Future<CrewProfileInfo> setProfilePhoto(String uploadId);

  // Manager (CRW-MGR).
  Future<ManagerSchedule> managerSchedule(DateTime date);
  Future<List<CrewRef>> managerCrew();
  Future<CrewJobDetail> managerJob(String jobId);
  Future<CrewJobDetail> managerCouldNotComplete(String jobId,
      {required String reasonKey, String note = '', String? uploadId});
  Future<CrewJobDetail> managerSkip(String jobId);
  Future<CrewJobDetail> managerReassign(String jobId, String crewId);

  // Manager attendance, working hours and reassign checks (CRW-MGR-03 to 05).
  Future<AttendanceDay> managerAttendance(DateTime date);

  /// [status] is one of [Attendance.all]. [start] is `HH:MM`, for a Late
  /// start only.
  Future<AttendanceResult> managerSetAttendance(String crewId,
      {required String status,
      required DateTime from,
      DateTime? to,
      String start = ''});
  Future<List<CrewHours>> managerHours();
  Future<HoursResult> managerSetHours(String crewId, List<HoursDay> days);
  Future<List<ReassignOption>> managerReassignOptions(String jobId);
}

/// The three steps of sending a file: ask for a signed URL, send the bytes
/// to it, confirm. The queue and the single uploads both use this.
abstract class UploadApi {
  Future<UploadTicket> requestUpload({
    required String purpose,
    String? jobId,
    required String kind,
    String? stage,
    required String contentType,
    required int sizeBytes,
  });

  /// Sends the file. A 403 means the link has expired: ask again.
  Future<void> sendFile(UploadTicket ticket, String path);

  Future<void> confirm(String uploadId);
}

class ApiCrewRepository implements CrewRepository, UploadApi {
  ApiCrewRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() run) async {
    try {
      return await run();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  Future<Map<String, dynamic>> _json(Future<Response<dynamic>> Function() run) =>
      _call(() async => ((await run()).data as Map).cast<String, dynamic>());

  Future<CrewJobDetail> _detail(Future<Response<dynamic>> Function() run) async =>
      CrewJobDetail.fromJson(await _json(run));

  @override
  Future<CrewVisitList> visits({DateTime? date, bool all = false}) async {
    final query = <String, dynamic>{
      if (all) 'all': true,
      if (!all && date != null) 'date': apiDate(date),
    };
    return CrewVisitList.fromJson(await _json(
        () => _dio.get('/v1/crew/visits', queryParameters: query)));
  }

  @override
  Future<CrewJobDetail> job(String jobId) =>
      _detail(() => _dio.get('/v1/crew/jobs/$jobId'));

  @override
  Future<CrewJobDetail> start(String jobId) =>
      _detail(() => _dio.post('/v1/crew/jobs/$jobId/start'));

  @override
  Future<CrewJobDetail> setChecked(String jobId, String itemId, bool checked) =>
      _detail(() => _dio.put('/v1/crew/jobs/$jobId/checklist/$itemId',
          data: {'checked': checked}));

  @override
  Future<CrewJobDetail> complete(String jobId) =>
      _detail(() => _dio.post('/v1/crew/jobs/$jobId/complete'));

  Map<String, dynamic> _reasonBody(
          String reasonKey, String note, String? uploadId) =>
      {
        'reason_key': reasonKey,
        'note': note,
        'upload_id': ?uploadId,
      };

  @override
  Future<CrewJobDetail> couldNotComplete(String jobId,
          {required String reasonKey, String note = '', String? uploadId}) =>
      _detail(() => _dio.post('/v1/crew/jobs/$jobId/could-not-complete',
          data: _reasonBody(reasonKey, note, uploadId)));

  @override
  Future<List<CrewReason>> reasons() => _call(() async {
        final r = await _dio.get('/v1/crew/reasons');
        return (r.data as List)
            .map((e) => CrewReason.fromJson((e as Map).cast<String, dynamic>()))
            .toList();
      });

  @override
  Future<CrewProfileInfo> profile() async {
    final body = await _json(() => _dio.get('/v1/crew/profile'));
    var hasPhoto = false;
    String? photoUrl;
    try {
      final photo = await _json(() => _dio.get('/v1/crew/profile/photo'));
      hasPhoto = photo['upload_id'] != null;
      photoUrl = photo['url'] as String?;
    } on ApiFailure {
      // The photo is a nicety. The details still show.
    }
    return CrewProfileInfo.fromJson(body, hasPhoto: hasPhoto, photoUrl: photoUrl);
  }

  @override
  Future<CrewProfileInfo> setProfilePhoto(String uploadId) async {
    await _json(() =>
        _dio.put('/v1/crew/profile/photo', data: {'upload_id': uploadId}));
    return profile();
  }

  @override
  Future<ManagerSchedule> managerSchedule(DateTime date) async =>
      ManagerSchedule.fromJson(await _json(() => _dio.get(
          '/v1/crew/manager/schedule',
          queryParameters: {'date': apiDate(date)})));

  @override
  Future<List<CrewRef>> managerCrew() => _call(() async {
        final r = await _dio.get('/v1/crew/manager/crew');
        return (r.data as List)
            .map((e) => CrewRef.fromJson((e as Map).cast<String, dynamic>()))
            .toList();
      });

  @override
  Future<CrewJobDetail> managerJob(String jobId) =>
      _detail(() => _dio.get('/v1/crew/manager/jobs/$jobId'));

  @override
  Future<CrewJobDetail> managerCouldNotComplete(String jobId,
          {required String reasonKey, String note = '', String? uploadId}) =>
      _detail(() => _dio.post(
          '/v1/crew/manager/jobs/$jobId/could-not-complete',
          data: _reasonBody(reasonKey, note, uploadId)));

  @override
  Future<CrewJobDetail> managerSkip(String jobId) =>
      _detail(() => _dio.post('/v1/crew/manager/jobs/$jobId/skip'));

  @override
  Future<CrewJobDetail> managerReassign(String jobId, String crewId) =>
      _detail(() => _dio.post('/v1/crew/manager/jobs/$jobId/reassign',
          data: {'crew_id': crewId}));

  @override
  Future<AttendanceDay> managerAttendance(DateTime date) async =>
      AttendanceDay.fromJson(await _json(() => _dio.get(
          '/v1/crew/manager/attendance',
          queryParameters: {'date': apiDate(date)})));

  @override
  Future<AttendanceResult> managerSetAttendance(String crewId,
          {required String status,
          required DateTime from,
          DateTime? to,
          String start = ''}) async =>
      AttendanceResult.fromJson(await _json(() => _dio.put(
          '/v1/crew/manager/attendance/$crewId',
          data: {
            'status': status,
            'from_date': apiDate(from),
            if (to != null) 'to_date': apiDate(to),
            if (start.isNotEmpty) 'start': start,
          })));

  @override
  Future<List<CrewHours>> managerHours() => _call(() async {
        final r = await _dio.get('/v1/crew/manager/hours');
        return (r.data as List)
            .map((e) => CrewHours.fromJson((e as Map).cast<String, dynamic>()))
            .toList();
      });

  @override
  Future<HoursResult> managerSetHours(String crewId, List<HoursDay> days) async =>
      HoursResult.fromJson(await _json(() => _dio.put(
          '/v1/crew/manager/hours/$crewId',
          data: {'working_hours': [for (final d in days) d.toJson()]})));

  @override
  Future<List<ReassignOption>> managerReassignOptions(String jobId) =>
      _call(() async {
        final r =
            await _dio.get('/v1/crew/manager/jobs/$jobId/reassign-options');
        return (r.data as List)
            .map((e) =>
                ReassignOption.fromJson((e as Map).cast<String, dynamic>()))
            .toList();
      });

  // ---- Uploads ---------------------------------------------------------------

  @override
  Future<UploadTicket> requestUpload({
    required String purpose,
    String? jobId,
    required String kind,
    String? stage,
    required String contentType,
    required int sizeBytes,
  }) async =>
      UploadTicket.fromJson(await _json(() => _dio.post('/v1/media/uploads',
          data: {
            'purpose': purpose,
            'job_id': ?jobId,
            'kind': kind,
            'stage': ?stage,
            'content_type': contentType,
            'size_bytes': sizeBytes,
          })));

  @override
  Future<void> sendFile(UploadTicket ticket, String path) async {
    final file = File(path);
    final length = await file.length();
    await _call(() => _dio.request<void>(
          ticket.url,
          data: file.openRead(),
          options: Options(
            method: ticket.method,
            headers: {...ticket.headers, Headers.contentLengthHeader: length},
            // A signed URL is its own credential. Our token must not go to it.
            extra: {'noAuth': true},
            sendTimeout: const Duration(minutes: 5),
          ),
        ));
  }

  @override
  Future<void> confirm(String uploadId) =>
      _call(() => _dio.post('/v1/media/uploads/$uploadId/confirm'));
}
