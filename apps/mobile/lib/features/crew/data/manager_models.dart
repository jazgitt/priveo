// Hand-written models for the Manager's attendance, working hours and
// reassign checks (`/v1/crew/manager/attendance`, `/hours`,
// `/jobs/{id}/reassign-options`). CRW-MGR-03 to CRW-MGR-05.

List<T> _list<T>(Object? v, T Function(Map<String, dynamic>) f) =>
    (v as List? ?? const [])
        .map((e) => f((e as Map).cast<String, dynamic>()))
        .toList();

/// The attendance values a Manager can set.
abstract final class Attendance {
  static const present = 'present';
  static const sick = 'Sick';
  static const leave = 'Leave';
  static const lateStart = 'Late start';

  static const all = [present, sick, leave, lateStart];
}

class AttendanceEntry {
  const AttendanceEntry({
    required this.crewId,
    required this.name,
    required this.role,
    required this.working,
    required this.start,
    required this.end,
    required this.status,
    required this.lateStart,
    required this.openJobs,
  });

  factory AttendanceEntry.fromJson(Map<String, dynamic> j) => AttendanceEntry(
        crewId: j['crew_id'] as String,
        name: j['name'] as String,
        role: (j['role'] as String?) ?? '',
        working: j['working'] == true,
        start: (j['start'] as String?) ?? '',
        end: (j['end'] as String?) ?? '',
        status: (j['status'] as String?) ?? Attendance.present,
        lateStart: (j['late_start'] as String?) ?? '',
        openJobs: (j['open_jobs'] as num?)?.toInt() ?? 0,
      );

  final String crewId;
  final String name;
  final String role;

  /// Whether the weekday's hours make this a working day.
  final bool working;
  final String start;
  final String end;

  /// present, Sick, Leave or Late start.
  final String status;
  final String lateStart;
  final int openJobs;
}

class AttendanceDay {
  const AttendanceDay(
      {required this.date, required this.society, required this.crew});

  factory AttendanceDay.fromJson(Map<String, dynamic> j) => AttendanceDay(
        date: DateTime.parse(j['date'] as String),
        society: (j['society'] as String?) ?? '',
        crew: _list(j['crew'], AttendanceEntry.fromJson),
      );

  final DateTime date;
  final String society;
  final List<AttendanceEntry> crew;
}

/// A job a change took off a crew member.
class ReleasedJob {
  const ReleasedJob({
    required this.jobId,
    required this.date,
    required this.service,
    required this.registration,
    required this.reassigned,
  });

  factory ReleasedJob.fromJson(Map<String, dynamic> j) => ReleasedJob(
        jobId: j['job_id'] as String,
        date: DateTime.parse(j['date'] as String),
        service: (j['service'] as String?) ?? '',
        registration: (j['registration'] as String?) ?? '',
        reassigned: j['reassigned'] == true,
      );

  final String jobId;
  final DateTime date;
  final String service;
  final String registration;

  /// False means the job waits on the admin's Needs scheduling list.
  final bool reassigned;
}

class AttendanceResult {
  const AttendanceResult({required this.attendance, required this.released});

  factory AttendanceResult.fromJson(Map<String, dynamic> j) => AttendanceResult(
        attendance: AttendanceDay.fromJson(
            (j['attendance'] as Map).cast<String, dynamic>()),
        released: _list(j['released_jobs'], ReleasedJob.fromJson),
      );

  final AttendanceDay attendance;
  final List<ReleasedJob> released;
}

/// One weekday of a crew member's hours.
class HoursDay {
  const HoursDay(
      {required this.day,
      required this.working,
      this.start = '',
      this.end = ''});

  factory HoursDay.fromJson(Map<String, dynamic> j) => HoursDay(
        day: j['day'] as String,
        working: j['working'] == true,
        start: (j['start'] as String?) ?? '',
        end: (j['end'] as String?) ?? '',
      );

  Map<String, dynamic> toJson() => {
        'day': day,
        'working': working,
        'start': working ? start : '',
        'end': working ? end : '',
      };

  HoursDay copyWith({bool? working, String? start, String? end}) => HoursDay(
        day: day,
        working: working ?? this.working,
        start: start ?? this.start,
        end: end ?? this.end,
      );

  final String day;
  final bool working;

  /// `HH:MM`, empty on a day off.
  final String start;
  final String end;
}

class CrewHours {
  const CrewHours(
      {required this.crewId,
      required this.name,
      required this.role,
      required this.days});

  factory CrewHours.fromJson(Map<String, dynamic> j) => CrewHours(
        crewId: j['crew_id'] as String,
        name: j['name'] as String,
        role: (j['role'] as String?) ?? '',
        days: _list(j['working_hours'], HoursDay.fromJson),
      );

  final String crewId;
  final String name;
  final String role;
  final List<HoursDay> days;
}

class HoursResult {
  const HoursResult({required this.hours, required this.released});

  factory HoursResult.fromJson(Map<String, dynamic> j) => HoursResult(
        hours: CrewHours.fromJson((j['hours'] as Map).cast<String, dynamic>()),
        released: _list(j['released_jobs'], ReleasedJob.fromJson),
      );

  final CrewHours hours;
  final List<ReleasedJob> released;
}

/// Who a job can go to, and what stops it when it cannot.
class ReassignOption {
  const ReassignOption({
    required this.crewId,
    required this.name,
    required this.role,
    required this.canAssign,
    this.problem = '',
    this.problemCode = '',
  });

  factory ReassignOption.fromJson(Map<String, dynamic> j) => ReassignOption(
        crewId: j['crew_id'] as String,
        name: j['name'] as String,
        role: (j['role'] as String?) ?? '',
        canAssign: j['can_assign'] == true,
        problem: (j['problem'] as String?) ?? '',
        problemCode: (j['problem_code'] as String?) ?? '',
      );

  final String crewId;
  final String name;
  final String role;
  final bool canAssign;
  final String problem;
  final String problemCode;
}
