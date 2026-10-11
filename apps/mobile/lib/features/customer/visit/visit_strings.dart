import 'package:intl/intl.dart';

/// English text of the service details, history and Home strip that came with
/// proof. The keys are in `lib/l10n/fragments/customer_proof.arb`.
class VisitStrings {
  const VisitStrings._();

  static String finishedAt(DateTime t) => 'Finished at ${clock(t)}';
  static String finishedShort(DateTime t) => clock(t);

  static String clock(DateTime t) => DateFormat('h:mm a').format(t);

  static const crewLine = 'Priveo crew';
  static String crewSociety(String society) =>
      society.isEmpty ? crewLine : '$crewLine · $society';
  static const crewPending = 'Crew member not assigned yet';

  static const checklistHeading = 'Checklist';
  static String checklistSummary(int done, int total) =>
      '$done of $total done';

  static const afterLabel = 'AFTER';
  static const beforeLabel = 'BEFORE';
  static const duringLabel = 'DURING';
  static String viewAll(int n) => 'View all ($n)';
  static String photosOf(int n) => n == 1 ? '1 photo' : '$n photos';

  static String stageLabel(String? stage) => switch (stage) {
    'Before' => 'Before',
    'During' => 'During',
    'After' => 'After',
    _ => 'Photo',
  };

  static String caption(String? stage, DateTime? at, String service) =>
      [stageLabel(stage), if (at != null) clock(at), service].join(' · ');

  static String videoTitle(String? stage, DateTime? at) =>
      ['Video', if (at != null) clock(at)].join(' · ');

  static const rateClean = 'Rate this clean';
  static const changeRating = 'Change rating';
  static String yourRating(int stars) => 'You rated this clean $stars of 5';
  static const reportIssue = 'Report an issue with this clean';
  static const ratingSaved = 'Thank you for your rating.';

  static const monthLabel = 'Month';
  static String historyFooter(String month, String? since) => since == null
      ? 'Showing $month'
      : 'Showing $month · Member since $since';
  static const loadMore = 'Load more';
  static const noRating = 'Not rated';
  static String stars(int n) => '$n star${n == 1 ? '' : 's'}';
  static const historyMonthEmpty = 'No services in this month.';

  static const todayDone = "Today's clean is done";
  static String todaySummary(String time, int done, int total, int photos) =>
      [
        'Finished at $time',
        if (total > 0) '$done of $total checks',
        if (photos > 0) VisitStrings.photosOf(photos),
      ].join(' · ');
  static const viewProof = 'View proof';
  static const rateToday = "Rate today's clean";
}
