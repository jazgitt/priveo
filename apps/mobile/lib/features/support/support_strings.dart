/// Text of the support screens. The same keys and words are in
/// `lib/l10n/fragments/support.arb`, which is merged into `app_en.arb` when the
/// slices are joined. A test keeps the two the same. When the merge is done,
/// each `t.xxx` can become `AppLocalizations.of(context).support_xxx`.
class SupportText {
  const SupportText();

  static const Map<String, String> all = {
    'support_title': 'Help and support',
    'support_call': 'Call support',
    'support_whatsapp': 'WhatsApp support',
    'support_hours': 'Support hours: {hours}',
    'support_report_issue': 'Report an issue',
    'support_my_complaints': 'My complaints',
    'support_complaints_in_progress': '{count} in progress',
    'support_give_feedback': 'Give feedback',
    'support_monthly_checkin': 'Monthly check-in',
    'support_cannot_open': 'We could not open that. Please try again.',
    'support_report_title': 'Report an issue',
    'support_issue_category': 'What went wrong?',
    'support_issue_choose': 'Choose what went wrong.',
    'support_issue_linked_visit': 'This report is linked to the clean you came from.',
    'support_issue_description': 'Describe what happened',
    'support_issue_description_required': 'Describe what happened.',
    'support_issue_send': 'Send report',
    'support_issue_sent': 'Thank you. We will reply within 4 hours.',
    'support_complaints_title': 'My complaints',
    'support_complaints_empty': 'You have not raised any complaints.',
    'support_complaint_raised_on': 'Raised {date}',
    'support_complaint_reply_hint': 'Write a reply',
    'support_complaint_send': 'Send',
    'support_complaint_resolved': 'This complaint is resolved. Raise a new one if the problem is back.',
    'support_thread_you': 'You',
    'support_thread_priveo': 'Priveo',
    'support_status_changed': 'Status: {status}',
    'support_feedback_title': 'Give feedback',
    'support_feedback_category': 'What is it about? (optional)',
    'support_feedback_rating': 'Your rating',
    'support_feedback_comment': 'Comments',
    'support_feedback_testimonial': 'Priveo may quote my feedback as a testimonial.',
    'support_feedback_send': 'Send',
    'support_feedback_thanks': 'Thank you for your feedback.',
    'support_star': 'Rate {n} out of 5',
    'support_rate_title': 'Rate this clean',
    'support_rate_positive_tags': 'What went well? (optional)',
    'support_rate_issue_tags': 'What could be better? (optional)',
    'support_rate_thanks': 'Thank you for rating this clean.',
    'support_checkin_title': 'Monthly check-in',
    'support_checkin_intro': 'How is Priveo doing for {vehicle}? Tap a star for any of these.',
    'support_checkin_comment': 'Anything else? (optional)',
    'support_checkin_submit': 'Submit',
    'support_checkin_thanks': 'Thank you. Your check-in is saved.',
    'support_checkin_none': 'There is no check-in to give right now.',
    'support_crew_ratings_title': 'Ratings',
    'support_crew_ratings_note': 'Customers rate each visit as a whole. A rating is never given to a crew member.',
    'support_crew_ratings_average': 'Average rating',
    'support_crew_ratings_count': '{count} ratings in the last {days} days',
    'support_crew_ratings_none': 'No ratings yet.',
    'support_alerts_title': 'Alerts',
    'support_alerts_unread': '{count} unread',
    'support_alerts_empty': 'No alerts.',
    'support_alerts_mark_all': 'Mark all as read',
  };

  /// The words for [key], with each `{name}` replaced from [args].
  String call(String key, [Map<String, Object> args = const {}]) {
    var text = all[key]!;
    args.forEach((k, v) => text = text.replaceAll('{$k}', '$v'));
    return text;
  }
}

const t = SupportText();
