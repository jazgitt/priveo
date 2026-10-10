// Hand-written models for the crew endpoints (`/v1/crew/visits`, jobs,
// manager, profile and `/v1/media`). They are not in the generated client
// yet. None of them carries a customer's name or mobile number (CRW-SCH-13).

DateTime? _date(Object? v) => v == null ? null : DateTime.parse(v as String);

DateTime? _time(Object? v) =>
    v == null ? null : DateTime.parse(v as String).toLocal();

List<T> _list<T>(Object? v, T Function(Map<String, dynamic>) f) =>
    (v as List? ?? const [])
        .map((e) => f((e as Map).cast<String, dynamic>()))
        .toList();

/// The statuses a job can have (CRW-SCH-07). "Skipped" is a job a Manager
/// skipped for operations.
abstract final class JobStatus {
  static const scheduled = 'Scheduled';
  static const inProgress = 'In progress';
  static const completed = 'Completed';
  static const couldNotComplete = 'Could not complete';
  static const skipped = 'Skipped';

  static bool isClosed(String status) =>
      status == completed || status == couldNotComplete || status == skipped;
}

class CrewVehicle {
  const CrewVehicle({
    required this.id,
    required this.registration,
    required this.make,
    required this.model,
    required this.category,
  });

  factory CrewVehicle.fromJson(Map<String, dynamic> j) => CrewVehicle(
        id: j['id'] as String,
        registration: (j['registration'] as String?) ?? '',
        make: (j['make'] as String?) ?? '',
        model: (j['model'] as String?) ?? '',
        category: (j['category'] as String?) ?? '',
      );

  final String id;
  final String registration;
  final String make;
  final String model;
  final String category;

  /// "Make Model", for the line under the registration.
  String get name => [make, model].where((p) => p.isNotEmpty).join(' ');

  /// What the crew look for: the plate, or the car's name when the plate is
  /// not on file yet.
  String get title => registration.isNotEmpty ? registration : name;
}

class CrewRef {
  const CrewRef({required this.id, required this.name});

  factory CrewRef.fromJson(Map<String, dynamic> j) =>
      CrewRef(id: j['id'] as String, name: (j['name'] as String?) ?? '');

  final String id;
  final String name;
}

class CrewJobCard {
  const CrewJobCard({
    required this.id,
    required this.visitId,
    required this.visitStatus,
    required this.date,
    required this.service,
    required this.status,
    required this.vehicle,
    required this.society,
    required this.parking,
    required this.startTime,
    required this.finishBy,
    required this.checklistTotal,
    required this.checklistDone,
    required this.assignedTo,
  });

  factory CrewJobCard.fromJson(Map<String, dynamic> j) => CrewJobCard(
        id: j['id'] as String,
        visitId: j['visit_id'] as String,
        visitStatus: j['visit_status'] as String,
        date: DateTime.parse(j['date'] as String),
        service: j['service'] as String,
        status: j['status'] as String,
        vehicle:
            CrewVehicle.fromJson((j['vehicle'] as Map).cast<String, dynamic>()),
        society: (j['society'] as String?) ?? '',
        parking: (j['parking'] as String?) ?? '',
        startTime: j['start_time'] as String?,
        finishBy: j['finish_by'] as String?,
        checklistTotal: (j['checklist_total'] as num?)?.toInt() ?? 0,
        checklistDone: (j['checklist_done'] as num?)?.toInt() ?? 0,
        assignedTo: j['assigned_to'] == null
            ? null
            : CrewRef.fromJson((j['assigned_to'] as Map).cast<String, dynamic>()),
      );

  final String id;
  final String visitId;
  final String visitStatus;
  final DateTime date;
  final String service;
  final String status;
  final CrewVehicle vehicle;
  final String society;

  /// For example `B2-14`. Empty when it is not on file.
  final String parking;

  /// `HH:MM`, the assigned slot (CRW-SCH-02).
  final String? startTime;

  /// `HH:MM`, the time the job must be finished by (CRW-SCH-04).
  final String? finishBy;
  final int checklistTotal;
  final int checklistDone;
  final CrewRef? assignedTo;

  bool get isClosed => JobStatus.isClosed(status);
}

class CrewVisitList {
  const CrewVisitList({
    required this.date,
    required this.society,
    required this.total,
    required this.done,
    required this.left,
    required this.jobs,
  });

  factory CrewVisitList.fromJson(Map<String, dynamic> j) => CrewVisitList(
        date: _date(j['date']),
        society: (j['society'] as String?) ?? '',
        total: (j['total'] as num).toInt(),
        done: (j['done'] as num).toInt(),
        left: (j['left'] as num).toInt(),
        jobs: _list(j['jobs'], CrewJobCard.fromJson),
      );

  /// Null when every card was asked for.
  final DateTime? date;
  final String society;
  final int total;
  final int done;
  final int left;
  final List<CrewJobCard> jobs;
}

class ChecklistEntry {
  const ChecklistEntry(
      {required this.id, required this.label, required this.checkedAt});

  factory ChecklistEntry.fromJson(Map<String, dynamic> j) => ChecklistEntry(
        id: j['id'] as String,
        label: j['label'] as String,
        checkedAt: _time(j['checked_at']),
      );

  final String id;
  final String label;
  final DateTime? checkedAt;

  bool get checked => checkedAt != null;
}

class ProofRequirements {
  const ProofRequirements({
    required this.photosRequired,
    required this.videosRequired,
    required this.photosConfirmed,
    required this.videosConfirmed,
    required this.pendingUploads,
  });

  factory ProofRequirements.fromJson(Map<String, dynamic> j) =>
      ProofRequirements(
        photosRequired: (j['photos_required'] as num).toInt(),
        videosRequired: (j['videos_required'] as num).toInt(),
        photosConfirmed: (j['photos_confirmed'] as num).toInt(),
        videosConfirmed: (j['videos_confirmed'] as num).toInt(),
        pendingUploads: (j['pending_uploads'] as num).toInt(),
      );

  final int photosRequired;
  final int videosRequired;
  final int photosConfirmed;
  final int videosConfirmed;
  final int pendingUploads;
}

class JobUpload {
  const JobUpload(
      {required this.id,
      required this.kind,
      required this.stage,
      required this.status});

  factory JobUpload.fromJson(Map<String, dynamic> j) => JobUpload(
        id: j['id'] as String,
        kind: j['kind'] as String,
        stage: j['stage'] as String?,
        status: j['status'] as String,
      );

  final String id;
  final String kind;
  final String? stage;
  final String status;
}

class JobOutcomeInfo {
  const JobOutcomeInfo(
      {required this.kind, required this.reasonKey, required this.note});

  factory JobOutcomeInfo.fromJson(Map<String, dynamic> j) => JobOutcomeInfo(
        kind: j['kind'] as String,
        reasonKey: j['reason_key'] as String?,
        note: (j['note'] as String?) ?? '',
      );

  final String kind;
  final String? reasonKey;
  final String note;
}

class CrewJobDetail {
  const CrewJobDetail({
    required this.job,
    required this.checklist,
    required this.requirements,
    required this.uploads,
    required this.missing,
    required this.canComplete,
    required this.outcome,
    required this.startedAt,
    required this.finishedAt,
  });

  factory CrewJobDetail.fromJson(Map<String, dynamic> j) => CrewJobDetail(
        job: CrewJobCard.fromJson((j['job'] as Map).cast<String, dynamic>()),
        checklist: _list(j['checklist'], ChecklistEntry.fromJson),
        requirements: ProofRequirements.fromJson(
            (j['requirements'] as Map).cast<String, dynamic>()),
        uploads: _list(j['uploads'], JobUpload.fromJson),
        missing: ((j['missing'] as List?) ?? const []).cast<String>(),
        canComplete: j['can_complete'] as bool,
        outcome: j['outcome'] == null
            ? null
            : JobOutcomeInfo.fromJson(
                (j['outcome'] as Map).cast<String, dynamic>()),
        startedAt: _time(j['started_at']),
        finishedAt: _time(j['finished_at']),
      );

  final CrewJobCard job;
  final List<ChecklistEntry> checklist;
  final ProofRequirements requirements;
  final List<JobUpload> uploads;
  final List<String> missing;
  final bool canComplete;
  final JobOutcomeInfo? outcome;
  final DateTime? startedAt;
  final DateTime? finishedAt;

  int get checklistLeft => checklist.where((c) => !c.checked).length;
}

class CrewReason {
  const CrewReason({required this.key, required this.label});

  factory CrewReason.fromJson(Map<String, dynamic> j) =>
      CrewReason(key: j['key'] as String, label: j['label'] as String);

  final String key;
  final String label;
}

class CrewProfileInfo {
  const CrewProfileInfo({
    required this.name,
    required this.mobile,
    required this.society,
    required this.role,
    required this.workingHours,
    required this.hasPhoto,
  });

  /// From `GET /v1/crew/profile`. The photo comes from its own call.
  factory CrewProfileInfo.fromJson(Map<String, dynamic> j,
          {bool hasPhoto = false}) =>
      CrewProfileInfo(
        name: j['name'] as String,
        mobile: j['mobile'] as String,
        society: (j['society'] as String?) ?? '',
        role: j['role'] as String,
        workingHours: [
          for (final d in (j['working_hours'] as List? ?? const []))
            if ((d as Map)['working'] == true)
              '${d['day']} ${d['start']} - ${d['end']}',
        ].join('\n'),
        hasPhoto: hasPhoto,
      );

  final String name;
  final String mobile;
  final String society;

  /// Member, Trainee or Manager.
  final String role;

  /// One line for each working day.
  final String workingHours;
  final bool hasPhoto;

  bool get isManager => role == 'Manager';
}

class TeamMemberJobs {
  const TeamMemberJobs(
      {required this.id,
      required this.name,
      required this.role,
      required this.jobs});

  factory TeamMemberJobs.fromJson(Map<String, dynamic> j) => TeamMemberJobs(
        id: j['id'] as String,
        name: j['name'] as String,
        role: (j['role'] as String?) ?? '',
        jobs: _list(j['jobs'], CrewJobCard.fromJson),
      );

  final String id;
  final String name;
  final String role;
  final List<CrewJobCard> jobs;
}

class ManagerSchedule {
  const ManagerSchedule({
    required this.date,
    required this.society,
    required this.crew,
    required this.unassigned,
  });

  factory ManagerSchedule.fromJson(Map<String, dynamic> j) => ManagerSchedule(
        date: DateTime.parse(j['date'] as String),
        society: (j['society'] as String?) ?? '',
        crew: _list(j['crew'], TeamMemberJobs.fromJson),
        unassigned: _list(j['unassigned'], CrewJobCard.fromJson),
      );

  final DateTime date;
  final String society;
  final List<TeamMemberJobs> crew;
  final List<CrewJobCard> unassigned;
}

/// The reply to "I want to upload this file": where to send it.
class UploadTicket {
  const UploadTicket({
    required this.id,
    required this.url,
    required this.method,
    required this.headers,
  });

  factory UploadTicket.fromJson(Map<String, dynamic> j) => UploadTicket(
        id: j['id'] as String,
        url: j['upload_url'] as String,
        method: (j['method'] as String?) ?? 'PUT',
        headers: ((j['headers'] as Map?) ?? const {}).cast<String, String>(),
      );

  final String id;
  final String url;
  final String method;
  final Map<String, String> headers;
}
