// Hand-written shapes for the admin quick actions (ADM-ACC-07). The home and
// the day schedule are new endpoints, so they are not in the generated client.

DateTime _dt(Object? v) => DateTime.parse(v as String);

List<T> _list<T>(Object? v, T Function(Map<String, dynamic>) f) => [
  for (final e in (v as List? ?? const [])) f(e as Map<String, dynamic>),
];

class QuickPayment {
  const QuickPayment({
    required this.id,
    required this.customerLabel,
    required this.amountRupees,
    required this.reference,
    this.vehicle = '',
  });

  final String id;
  final String customerLabel;
  final int amountRupees;
  final String reference;
  final String vehicle;

  factory QuickPayment.fromJson(Map<String, dynamic> j) => QuickPayment(
    id: j['id'] as String,
    customerLabel: j['customer_label'] as String,
    amountRupees: j['amount_rupees'] as int,
    reference: j['reference'] as String,
    vehicle: (j['vehicle'] as String?) ?? '',
  );
}

class SocietyRef {
  const SocietyRef({required this.id, required this.name});

  final String id;
  final String name;

  factory SocietyRef.fromJson(Map<String, dynamic> j) =>
      SocietyRef(id: j['id'] as String, name: j['name'] as String);
}

class QuickHome {
  const QuickHome({
    required this.alertCount,
    required this.needsSchedulingCount,
    required this.paymentsToConfirm,
    this.paymentsToConfirmCount = 0,
    this.openComplaintsCount = 0,
    this.societies = const [],
  });

  final int alertCount;
  final int needsSchedulingCount;
  final List<QuickPayment> paymentsToConfirm;
  final int paymentsToConfirmCount;
  final int openComplaintsCount;
  final List<SocietyRef> societies;

  factory QuickHome.fromJson(Map<String, dynamic> j) => QuickHome(
    alertCount: j['alert_count'] as int,
    needsSchedulingCount: j['needs_scheduling_count'] as int,
    paymentsToConfirm: _list(j['payments_to_confirm'], QuickPayment.fromJson),
    paymentsToConfirmCount: (j['payments_to_confirm_count'] as int?) ?? 0,
    openComplaintsCount: (j['open_complaints_count'] as int?) ?? 0,
    societies: _list(j['societies'], SocietyRef.fromJson),
  );
}

class ThreadUpdate {
  const ThreadUpdate({
    required this.authorRole,
    required this.note,
    required this.status,
    required this.createdAt,
  });

  final String authorRole;
  final String note;
  final String? status;
  final DateTime createdAt;

  factory ThreadUpdate.fromJson(Map<String, dynamic> j) => ThreadUpdate(
    authorRole: j['author_role'] as String,
    note: (j['note'] as String?) ?? '',
    status: j['status'] as String?,
    createdAt: _dt(j['created_at']),
  );
}

class QuickComplaint {
  const QuickComplaint({
    required this.id,
    required this.displayId,
    required this.category,
    required this.description,
    required this.status,
    required this.createdAt,
    required this.customerName,
    required this.society,
    required this.flat,
    required this.overdue,
    this.latestNote,
    this.updates = const [],
  });

  final String id;
  final String displayId;
  final String category;
  final String description;
  final String status;
  final DateTime createdAt;
  final String customerName;
  final String society;
  final String flat;
  final bool overdue;
  final String? latestNote;
  final List<ThreadUpdate> updates;

  factory QuickComplaint.fromJson(Map<String, dynamic> j) => QuickComplaint(
    id: j['id'] as String,
    displayId: j['display_id'] as String,
    category: j['category'] as String,
    description: j['description'] as String,
    status: j['status'] as String,
    createdAt: _dt(j['created_at']),
    customerName: (j['customer_name'] as String?) ?? '',
    society: (j['society'] as String?) ?? '',
    flat: (j['flat'] as String?) ?? '',
    overdue: (j['overdue'] as bool?) ?? false,
    latestNote: j['latest_note'] as String?,
    updates: _list(j['updates'], ThreadUpdate.fromJson),
  );
}

class QuickFeedback {
  const QuickFeedback({
    required this.id,
    required this.category,
    required this.rating,
    required this.comment,
    required this.customerName,
    required this.society,
    required this.createdAt,
  });

  final String id;
  final String? category;
  final int? rating;
  final String comment;
  final String customerName;
  final String society;
  final DateTime createdAt;

  factory QuickFeedback.fromJson(Map<String, dynamic> j) => QuickFeedback(
    id: j['id'] as String,
    category: j['category'] as String?,
    rating: j['rating'] as int?,
    comment: (j['comment'] as String?) ?? '',
    customerName: (j['customer_name'] as String?) ?? '',
    society: (j['society'] as String?) ?? '',
    createdAt: _dt(j['created_at']),
  );
}

class QuickRatings {
  const QuickRatings({
    required this.count,
    required this.average,
    required this.tagCounts,
  });

  final int count;
  final double? average;
  final Map<String, int> tagCounts;

  factory QuickRatings.fromJson(Map<String, dynamic> j) => QuickRatings(
    count: j['count'] as int,
    average: (j['average'] as num?)?.toDouble(),
    tagCounts: {
      for (final e in ((j['tag_counts'] as Map?) ?? const {}).entries)
        e.key as String: e.value as int,
    },
  );
}

/// A job on the needs-scheduling list.
class QuickJob {
  const QuickJob({
    required this.id,
    required this.date,
    required this.vehicle,
    required this.registration,
    required this.service,
    required this.status,
    this.reason = '',
  });

  final String id;
  final DateTime date;
  final String vehicle;
  final String registration;
  final String service;
  final String status;
  final String reason;

  factory QuickJob.fromJson(Map<String, dynamic> j) => QuickJob(
    id: j['id'] as String,
    date: DateTime.parse(j['date'] as String),
    vehicle: (j['vehicle'] as String?) ?? '',
    registration: (j['registration'] as String?) ?? '',
    service: j['service'] as String,
    status: j['status'] as String,
    reason: (j['reason'] as String?) ?? '',
  );
}

class DayJob {
  const DayJob({
    required this.id,
    required this.time,
    required this.endTime,
    required this.vehicle,
    required this.registration,
    required this.service,
    required this.status,
    required this.late,
  });

  final String id;
  final String? time;
  final String? endTime;
  final String vehicle;
  final String registration;
  final String service;
  final String status;
  final bool late;

  factory DayJob.fromJson(Map<String, dynamic> j) => DayJob(
    id: j['id'] as String,
    time: j['time'] as String?,
    endTime: j['end_time'] as String?,
    vehicle: (j['vehicle'] as String?) ?? '',
    registration: (j['registration'] as String?) ?? '',
    service: j['service'] as String,
    status: j['status'] as String,
    late: (j['late'] as bool?) ?? false,
  );
}

class DayCrew {
  const DayCrew({
    required this.crewId,
    required this.crewName,
    required this.jobs,
  });

  /// Null for the jobs that have no crew member yet.
  final String? crewId;
  final String crewName;
  final List<DayJob> jobs;

  factory DayCrew.fromJson(Map<String, dynamic> j) => DayCrew(
    crewId: j['crew_id'] as String?,
    crewName: j['crew_name'] as String,
    jobs: _list(j['jobs'], DayJob.fromJson),
  );
}

class DaySchedule {
  const DaySchedule({
    required this.date,
    required this.scheduleStatus,
    required this.total,
    required this.done,
    required this.left,
    required this.crew,
  });

  final DateTime date;
  final String? scheduleStatus;
  final int total;
  final int done;
  final int left;
  final List<DayCrew> crew;

  factory DaySchedule.fromJson(Map<String, dynamic> j) => DaySchedule(
    date: DateTime.parse(j['date'] as String),
    scheduleStatus: j['schedule_status'] as String?,
    total: j['total'] as int,
    done: j['done'] as int,
    left: j['left'] as int,
    crew: _list(j['crew'], DayCrew.fromJson),
  );
}

class DayCapacity {
  const DayCapacity({
    required this.date,
    required this.capacityMinutes,
    required this.demandMinutes,
    required this.scheduledMinutes,
    required this.overCapacity,
  });

  final DateTime date;
  final int capacityMinutes;
  final int demandMinutes;
  final int scheduledMinutes;
  final bool overCapacity;

  factory DayCapacity.fromJson(Map<String, dynamic> j) => DayCapacity(
    date: DateTime.parse(j['date'] as String),
    capacityMinutes: j['capacity_minutes'] as int,
    demandMinutes: j['demand_minutes'] as int,
    scheduledMinutes: j['scheduled_minutes'] as int,
    overCapacity: j['over_capacity'] as bool,
  );
}
