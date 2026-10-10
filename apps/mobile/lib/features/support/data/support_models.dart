// Hand-written copies of the support API shapes. They move to the generated
// client when the contract is exported with the support module.

class SupportContact {
  const SupportContact({
    required this.helpline,
    required this.whatsapp,
    required this.hours,
    required this.complaintsInProgress,
  });

  final String helpline;
  final String whatsapp;
  final String hours;
  final int complaintsInProgress;

  factory SupportContact.fromJson(Map<String, dynamic> j) => SupportContact(
        helpline: j['helpline'] as String,
        whatsapp: j['whatsapp'] as String,
        hours: j['hours'] as String,
        complaintsInProgress: j['complaints_in_progress'] as int,
      );
}

class OptionItem {
  const OptionItem({required this.id, required this.name, this.description = ''});

  final String id;
  final String name;
  final String description;

  factory OptionItem.fromJson(Map<String, dynamic> j) => OptionItem(
        id: j['id'] as String,
        name: j['name'] as String,
        description: (j['description'] as String?) ?? '',
      );
}

class SupportOptions {
  const SupportOptions({
    required this.issueCategories,
    required this.feedbackCategories,
    required this.positiveTags,
    required this.checkinCategories,
  });

  final List<String> issueCategories;
  final List<OptionItem> feedbackCategories;
  final List<OptionItem> positiveTags;
  final List<OptionItem> checkinCategories;

  static List<OptionItem> _items(Object? v) => [
        for (final e in (v as List)) OptionItem.fromJson(e as Map<String, dynamic>)
      ];

  factory SupportOptions.fromJson(Map<String, dynamic> j) => SupportOptions(
        issueCategories: [for (final e in (j['issue_categories'] as List)) e as String],
        feedbackCategories: _items(j['feedback_categories']),
        positiveTags: _items(j['positive_tags']),
        checkinCategories: _items(j['checkin_categories']),
      );
}

class ThreadEntry {
  const ThreadEntry({
    required this.id,
    required this.authorRole,
    required this.note,
    required this.status,
    required this.createdAt,
  });

  final String id;

  /// `customer` or `admin`.
  final String authorRole;
  final String note;
  final String? status;
  final DateTime createdAt;

  bool get fromCustomer => authorRole == 'customer';

  factory ThreadEntry.fromJson(Map<String, dynamic> j) => ThreadEntry(
        id: j['id'] as String,
        authorRole: j['author_role'] as String,
        note: (j['note'] as String?) ?? '',
        status: j['status'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}

class Complaint {
  const Complaint({
    required this.id,
    required this.displayId,
    required this.category,
    required this.description,
    required this.status,
    required this.createdAt,
    required this.latestNote,
    this.updates = const [],
  });

  final String id;

  /// `#C-0007`.
  final String displayId;
  final String category;
  final String description;

  /// `Raised`, `In progress` or `Resolved`.
  final String status;
  final DateTime createdAt;
  final String? latestNote;
  final List<ThreadEntry> updates;

  bool get isResolved => status == 'Resolved';

  /// 1 to 3, for the progress bar (CMP-02).
  int get step => switch (status) {
        'Resolved' => 3,
        'In progress' => 2,
        _ => 1,
      };

  factory Complaint.fromJson(Map<String, dynamic> j) => Complaint(
        id: j['id'] as String,
        displayId: j['display_id'] as String,
        category: j['category'] as String,
        description: j['description'] as String,
        status: j['status'] as String,
        createdAt: DateTime.parse(j['created_at'] as String),
        latestNote: j['latest_note'] as String?,
        updates: [
          for (final e in (j['updates'] as List? ?? const []))
            ThreadEntry.fromJson(e as Map<String, dynamic>)
        ],
      );
}

class PendingCheckIn {
  const PendingCheckIn({
    required this.subscriptionId,
    required this.vehicleLabel,
    required this.cycleStart,
  });

  final String subscriptionId;
  final String vehicleLabel;
  final String cycleStart;

  factory PendingCheckIn.fromJson(Map<String, dynamic> j) => PendingCheckIn(
        subscriptionId: j['subscription_id'] as String,
        vehicleLabel: j['vehicle_label'] as String,
        cycleStart: j['cycle_start'] as String,
      );
}

/// General ratings only: no names, tags or comments (CRW-RAT-01).
class CrewRatings {
  const CrewRatings({
    required this.periodDays,
    required this.count,
    required this.average,
    required this.stars,
  });

  final int periodDays;
  final int count;
  final double? average;

  /// Star (1 to 5) to how many ratings gave it.
  final Map<int, int> stars;

  factory CrewRatings.fromJson(Map<String, dynamic> j) => CrewRatings(
        periodDays: j['period_days'] as int,
        count: j['count'] as int,
        average: (j['average'] as num?)?.toDouble(),
        stars: {
          for (final e in (j['stars'] as Map<String, dynamic>).entries)
            int.parse(e.key): e.value as int
        },
      );
}
