/// Text of the admin quick-action screens. The same keys and words are in
/// `lib/l10n/fragments/admin_quick.arb`, which is merged into `app_en.arb` when
/// the slices are joined. A test keeps the two the same.
class AdminQuickText {
  const AdminQuickText();

  static const Map<String, String> all = {
    'adminq_home_complaints': 'Complaints',
    'adminq_home_feedback': 'Feedback and ratings',
    'adminq_home_needs_scheduling': 'Needs scheduling',
    'adminq_home_day': 'Day schedule',
    'adminq_home_capacity': 'Capacity',
    'adminq_home_open_complaints': 'Open complaints',
    'adminq_home_to_confirm': 'To confirm',
    'adminq_home_more_payments': '{count} more to confirm',
    'adminq_filter_all': 'All',
    'adminq_status_raised': 'Raised',
    'adminq_status_in_progress': 'In progress',
    'adminq_status_resolved': 'Resolved',
    'adminq_complaints_title': 'Complaints',
    'adminq_complaints_empty': 'No complaints.',
    'adminq_complaint_overdue': 'Open for more than 4 hours',
    'adminq_complaint_raised_on': 'Raised {date}',
    'adminq_complaint_status': 'Status',
    'adminq_complaint_note_hint': 'Write a note',
    'adminq_complaint_note_required': 'Write a note first.',
    'adminq_complaint_add_note': 'Add note',
    'adminq_complaint_save_status': 'Save status',
    'adminq_complaint_saved': 'Saved.',
    'adminq_complaint_thread': 'History',
    'adminq_complaint_by_customer': 'Customer',
    'adminq_complaint_by_admin': 'Priveo',
    'adminq_complaint_status_changed': 'Status: {status}',
    'adminq_feedback_title': 'Feedback and ratings',
    'adminq_feedback_empty': 'No feedback yet.',
    'adminq_feedback_ratings': 'Visit ratings',
    'adminq_feedback_average': 'Average {average} from {count} ratings',
    'adminq_feedback_no_ratings': 'No ratings yet.',
    'adminq_feedback_stars': '{n} stars',
    'adminq_needs_title': 'Needs scheduling',
    'adminq_needs_empty': 'Every job has a crew member.',
    'adminq_day_title': 'Day schedule',
    'adminq_day_summary': '{total} jobs, {done} done, {left} left',
    'adminq_day_empty': 'No jobs on this date.',
    'adminq_day_status': 'Schedule: {status}',
    'adminq_day_all_societies': 'All societies',
    'adminq_day_previous': 'Previous day',
    'adminq_day_next': 'Next day',
    'adminq_day_late': 'Late',
    'adminq_day_no_time': 'No time',
    'adminq_capacity_title': 'Capacity',
    'adminq_capacity_empty': 'Choose a society to see its capacity.',
    'adminq_capacity_line':
        'Crew {capacity} min, work {demand} min, placed {scheduled} min',
    'adminq_capacity_over': 'Over capacity',
    'adminq_capacity_previous': 'Previous week',
    'adminq_capacity_next': 'Next week',
    'adminq_society': 'Society',
  };

  /// The words for [key], with each `{name}` replaced from [args].
  String call(String key, [Map<String, Object> args = const {}]) {
    var text = all[key]!;
    args.forEach((k, v) => text = text.replaceAll('{$k}', '$v'));
    return text;
  }
}

const q = AdminQuickText();
