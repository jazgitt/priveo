import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/crew/capture/media_capture.dart';
import 'package:priveo/features/crew/crew_providers.dart';
import 'package:priveo/features/crew/data/crew_models.dart';
import 'package:priveo/features/crew/data/crew_repository.dart';
import 'package:priveo/features/crew/data/manager_models.dart';
import 'package:priveo/features/crew/upload/upload_queue.dart';
import 'package:priveo/l10n/app_localizations.dart';

Map<String, dynamic> cardJson({
  String id = 'j1',
  String status = 'Scheduled',
  String registration = 'MH12AB1234',
  String service = 'Cleaning-External',
  String date = '2026-11-07',
  Map<String, dynamic>? assignedTo,
  int done = 0,
  bool locked = false,
  bool current = false,
}) =>
    {
      'id': id,
      'visit_id': 'v-$id',
      'visit_status': status,
      'date': date,
      'service': service,
      'status': status,
      'vehicle': {
        'id': 'car-$id',
        'registration': registration,
        'make': 'Hyundai',
        'model': 'Creta',
        'category': 'SUV',
      },
      'society': 'Green Meadows',
      'parking': 'B2-14',
      'start_time': '06:40',
      'finish_by': '07:00',
      'checklist_total': 2,
      'checklist_done': done,
      'assigned_to': assignedTo,
      'locked': locked,
      'current': current,
    };

/// A crew backend in memory. It follows the server's rules for completing a
/// job: every item checked, the minimum proof confirmed, nothing unconfirmed.
class FakeCrewBackend implements CrewRepository, UploadApi {
  FakeCrewBackend({this.role = 'Member', this.requiredPhotos = 1}) {
    jobs['j1'] = _Job('j1', 'MH12AB1234', requiredPhotos);
    jobs['j2'] = _Job('j2', 'MH12CD5678', requiredPhotos)
      ..assignedTo = {'id': 'c2', 'name': 'Sunil'};
  }

  String role;
  int requiredPhotos;
  bool offline = false;
  final jobs = <String, _Job>{};
  final visitCalls = <String>[];
  final skipped = <String>[];
  void markMissed(String id, {String service = 'Cleaning-Internal'}) => jobs[id]!
    ..status = 'Could not complete'
    ..service = service;
  final rescheduled = <String>[];
  final reassigned = <String, String>{};
  final couldNot = <String, Map<String, String?>>{};
  int sendCount = 0;

  void _guard() {
    if (offline) throw const ApiFailure();
  }

  CrewJobDetail _detail(_Job j) {
    final left = j.items.values.where((c) => !c).length;
    final missing = <String>[
      if (left > 0) '$left checklist items not checked',
      if (j.photos < j.requiredPhotos) 'more photos to upload',
    ];
    return CrewJobDetail.fromJson({
      'job': cardJson(
          id: j.id,
          status: j.status,
          registration: j.registration,
          service: j.service,
          assignedTo: j.assignedTo,
          done: j.items.values.where((c) => c).length),
      'checklist': [
        for (final e in j.items.entries)
          {
            'id': e.key,
            'label': 'Item ${e.key}',
            'checked_at': e.value ? '2026-11-07T01:00:00+00:00' : null,
          },
      ],
      'requirements': {
        'photos_required': j.requiredPhotos,
        'videos_required': 0,
        'photos_confirmed': j.photos,
        'videos_confirmed': 0,
        'pending_uploads': 0,
      },
      'uploads': const [],
      'missing': missing,
      'can_complete': missing.isEmpty && !JobStatus.isClosed(j.status),
      'outcome': j.outcome,
      'started_at': null,
      'finished_at': null,
    });
  }

  @override
  Future<CrewVisitList> visits({DateTime? date, bool all = false}) async {
    _guard();
    visitCalls.add(all ? 'all' : apiDate(date!));
    final mine = jobs.values.where((j) => j.assignedTo == null).toList();
    final cards = [
      for (final j in mine)
        CrewJobCard.fromJson(cardJson(
            id: j.id, status: j.status, registration: j.registration)),
    ];
    final done = cards.where((c) => c.isClosed).length;
    return CrewVisitList(
        date: date,
        society: 'Green Meadows',
        total: cards.length,
        done: done,
        left: cards.length - done,
        jobs: cards);
  }

  @override
  Future<CrewJobDetail> job(String jobId) async {
    _guard();
    return _detail(jobs[jobId]!);
  }

  @override
  Future<CrewJobDetail> start(String jobId) async {
    _guard();
    jobs[jobId]!.status = 'In progress';
    return _detail(jobs[jobId]!);
  }

  @override
  Future<CrewJobDetail> setChecked(
      String jobId, String itemId, bool checked) async {
    _guard();
    jobs[jobId]!.items[itemId] = checked;
    return _detail(jobs[jobId]!);
  }

  @override
  Future<CrewJobDetail> complete(String jobId) async {
    _guard();
    final j = jobs[jobId]!;
    if (!_detail(j).canComplete) {
      throw const ApiFailure(
          code: 'job_not_ready',
          message: 'This job cannot be completed yet.',
          statusCode: 409);
    }
    j.status = 'Completed';
    return _detail(j);
  }

  @override
  Future<CrewJobDetail> couldNotComplete(String jobId,
      {required String reasonKey, String note = '', String? uploadId}) async {
    _guard();
    couldNot[jobId] = {'reason': reasonKey, 'note': note, 'upload': uploadId};
    jobs[jobId]!.status = 'Could not complete';
    jobs[jobId]!.outcome = {
      'kind': 'could_not_complete',
      'reason_key': reasonKey,
      'note': note,
      'at': '2026-11-07T01:00:00+00:00',
    };
    return _detail(jobs[jobId]!);
  }

  @override
  Future<List<CrewReason>> reasons() async => const [
        CrewReason(key: 'car_locked', label: 'Car is locked'),
        CrewReason(key: 'other', label: 'Other'),
      ];

  @override
  Future<CrewProfileInfo> profile() async {
    _guard();
    return CrewProfileInfo.fromJson({
      'name': 'Ravi Kumar',
      'mobile': '9000000002',
      'society': 'Green Meadows',
      'role': role,
      'working_hours': [
        {'day': 'Mon', 'working': true, 'start': '06:00', 'end': '14:00'},
        {'day': 'Sun', 'working': false, 'start': '', 'end': ''},
      ],
    });
  }

  @override
  Future<CrewProfileInfo> setProfilePhoto(String uploadId) => profile();

  @override
  Future<ManagerSchedule> managerSchedule(DateTime date) async {
    _guard();
    CrewJobCard card(_Job j) => CrewJobCard.fromJson(cardJson(
        id: j.id,
        status: j.status,
        registration: j.registration,
        assignedTo: j.assignedTo ?? {'id': 'c1', 'name': 'Ravi Kumar'}));
    return ManagerSchedule(
      date: date,
      society: 'Green Meadows',
      crew: [
        TeamMemberJobs(
            id: 'c1',
            name: 'Ravi Kumar',
            role: 'Manager',
            jobs: [
              for (final j in jobs.values)
                if (j.assignedTo == null || j.assignedTo!['id'] == 'c1') card(j)
            ]),
        TeamMemberJobs(
            id: 'c2',
            name: 'Sunil',
            role: 'Member',
            jobs: [
              for (final j in jobs.values)
                if (j.assignedTo?['id'] == 'c2') card(j)
            ]),
      ],
      unassigned: const [],
    );
  }

  @override
  Future<List<CrewRef>> managerCrew() async => const [
        CrewRef(id: 'c1', name: 'Ravi Kumar'),
        CrewRef(id: 'c2', name: 'Sunil'),
      ];

  @override
  Future<CrewJobDetail> managerJob(String jobId) => job(jobId);

  @override
  Future<CrewJobDetail> managerCouldNotComplete(String jobId,
          {required String reasonKey, String note = '', String? uploadId}) =>
      couldNotComplete(jobId,
          reasonKey: reasonKey, note: note, uploadId: uploadId);

  @override
  Future<CrewJobDetail> managerSkip(String jobId) async {
    _guard();
    skipped.add(jobId);
    jobs[jobId]!.status = 'Skipped';
    return _detail(jobs[jobId]!);
  }

  @override
  Future<CrewJobDetail> managerReschedule(String jobId) async {
    _guard();
    rescheduled.add(jobId);
    return _detail(jobs[jobId]!);
  }

  @override
  Future<CrewJobDetail> managerReassign(String jobId, String crewId) async {
    _guard();
    reassigned[jobId] = crewId;
    jobs[jobId]!.assignedTo = {'id': crewId, 'name': 'Sunil'};
    return _detail(jobs[jobId]!);
  }

  // ---- Manager attendance, hours and reassign checks ---------------------------

  /// Crew ids the reassign check refuses, with the words the server gives.
  final blockedReassign = <String, String>{};
  final attendanceSet = <String, String>{};
  final hoursSet = <String, List<HoursDay>>{};
  final _attendance = <String, String>{};

  @override
  Future<AttendanceDay> managerAttendance(DateTime date) async {
    _guard();
    AttendanceEntry entry(String id, String name, String role, int open) =>
        AttendanceEntry(
            crewId: id,
            name: name,
            role: role,
            working: true,
            start: '06:00',
            end: '11:00',
            status: _attendance[id] ?? Attendance.present,
            lateStart: '',
            openJobs: open);
    return AttendanceDay(date: date, society: 'Green Meadows', crew: [
      entry('c1', 'Ravi Kumar', 'Manager', 1),
      entry('c2', 'Sunil', 'Member', 1),
    ]);
  }

  @override
  Future<AttendanceResult> managerSetAttendance(String crewId,
      {required String status,
      required DateTime from,
      DateTime? to,
      String start = ''}) async {
    _guard();
    attendanceSet[crewId] = status;
    _attendance[crewId] = status;
    return AttendanceResult(
        attendance: await managerAttendance(from),
        released: status == Attendance.present
            ? const []
            : [
                ReleasedJob(
                    jobId: 'j2',
                    date: from,
                    service: 'Cleaning-External',
                    registration: 'MH12CD5678',
                    reassigned: false)
              ]);
  }

  CrewHours _hours(String id, String name, String role) => CrewHours(
      crewId: id,
      name: name,
      role: role,
      days: hoursSet[id] ??
          [
            for (final d in const [
              'Monday',
              'Tuesday',
              'Wednesday',
              'Thursday',
              'Friday',
              'Saturday',
              'Sunday'
            ])
              HoursDay(day: d, working: d != 'Sunday', start: '06:00', end: '11:00'),
          ]);

  @override
  Future<List<CrewHours>> managerHours() async {
    _guard();
    return [_hours('c1', 'Ravi Kumar', 'Manager'), _hours('c2', 'Sunil', 'Member')];
  }

  @override
  Future<HoursResult> managerSetHours(String crewId, List<HoursDay> days) async {
    _guard();
    hoursSet[crewId] = days;
    return HoursResult(
        hours: _hours(crewId, crewId == 'c1' ? 'Ravi Kumar' : 'Sunil', 'Member'),
        released: const []);
  }

  @override
  Future<List<ReassignOption>> managerReassignOptions(String jobId) async {
    _guard();
    return [
      for (final c in await managerCrew())
        ReassignOption(
            crewId: c.id,
            name: c.name,
            role: 'Member',
            canAssign: !blockedReassign.containsKey(c.id),
            problem: blockedReassign[c.id] ?? '',
            problemCode:
                blockedReassign.containsKey(c.id) ? 'crew_not_working' : ''),
    ];
  }

  // ---- Uploads ---------------------------------------------------------------

  final _kinds = <String, String>{};
  final _jobOf = <String, String>{};

  @override
  Future<UploadTicket> requestUpload({
    required String purpose,
    String? jobId,
    required String kind,
    String? stage,
    required String contentType,
    required int sizeBytes,
  }) async {
    _guard();
    final id = 'u${_kinds.length + 1}';
    _kinds[id] = '$purpose:$kind';
    if (jobId != null) _jobOf[id] = jobId;
    return UploadTicket(id: id, url: '/v1/media/local/$id', method: 'PUT', headers: const {});
  }

  @override
  Future<void> sendFile(UploadTicket ticket, String path) async {
    _guard();
    sendCount++;
  }

  @override
  Future<void> confirm(String uploadId) async {
    _guard();
    final job = _jobOf[uploadId];
    if (job != null && _kinds[uploadId] == 'proof:photo') jobs[job]!.photos++;
  }
}

class _Job {
  _Job(this.id, this.registration, this.requiredPhotos);

  final String id;
  final String registration;
  final int requiredPhotos;
  String status = 'Scheduled';
  String service = 'Cleaning-External';
  int photos = 0;
  Map<String, String>? assignedTo;
  Map<String, dynamic>? outcome;
  final items = <String, bool>{'a': false, 'b': false};
}

class FakeCapture implements MediaCapture {
  int photos = 0;
  CapturedFile? next;

  @override
  Future<CapturedFile?> photo({required bool camera}) async {
    photos++;
    return next ??
        CapturedFile(
            path: '/tmp/p$photos.jpg',
            contentType: 'image/jpeg',
            sizeBytes: 2048,
            video: false);
  }

  @override
  Future<CapturedFile?> video({required bool camera}) async => next ??
      const CapturedFile(
          path: '/tmp/v.mp4',
          contentType: 'video/mp4',
          sizeBytes: 4096,
          video: true);
}

/// Shows [home] with fake data sources, in the crew look. Returns the
/// queue so a test can drive it.
Future<UploadQueue> pumpCrew(
  WidgetTester tester,
  Widget home, {
  required FakeCrewBackend backend,
  FakeCapture? capture,
  List<Override> extra = const [],
}) async {
  tester.view.physicalSize = const Size(800, 1800);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final queue = UploadQueue(
      api: backend,
      store: MemoryUploadQueueStore(),
      retryAfter: Duration.zero);
  addTearDown(queue.dispose);
  await tester.pumpWidget(ProviderScope(
    retry: (_, _) => null,
    overrides: [
      crewRepositoryProvider.overrideWithValue(backend),
      uploadApiProvider.overrideWithValue(backend),
      uploadQueueProvider.overrideWithValue(queue),
      mediaCaptureProvider.overrideWithValue(capture ?? FakeCapture()),
      ...extra,
    ],
    child: MaterialApp(
      theme: crewTheme,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: home,
    ),
  ));
  await tester.pumpAndSettle();
  return queue;
}
