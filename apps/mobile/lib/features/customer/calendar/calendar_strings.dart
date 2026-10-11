/// English text of the calendar day card and the Home schedule items
/// (CAL-05 to CAL-10, HOME-01, HOME-04, HOME-08, SCHED-02, SUB-08).
class CalStrings {
  const CalStrings._();

  static const legendPaused = 'Paused';
  static const legendExpected = 'Expected';
  static const expectedChip = 'Expected';
  static const pausedChip = 'Paused';
  static const expectedNote =
      'Expected visit. It is confirmed when the week is planned.';
  static const pausedNote = 'Your service is paused on this date.';
  static const changeRequested = 'Change requested, awaiting Priveo';

  static String changeRequestedAt(String time) =>
      'Change requested, awaiting Priveo. New cutoff time: $time.';

  static String missedCovered(String date) => 'Missed. Covered on $date';
  static String missedRescheduled(String date) =>
      'Missed. Rescheduled on $date';

  static String crewAt(String name, String start, String end) =>
      '$name, $start to $end';

  static String crewNameOnly(String name) => name;

  static String renews(String date) => 'Your plan renews on $date.';

  static const viewCalendar = 'View calendar';

  static String pausePreview(int visits, String? from, String? to) {
    final base = visits == 1
        ? '1 visit will be paused.'
        : '$visits visits will be paused.';
    return from == null || to == null
        ? base
        : '$base Your renewal moves from $from to $to.';
  }

  static const skipDate = 'Skip this date';
  static const undoSkip = 'Undo skip';
  static const changeCutoff = 'Change cutoff time';
  static const chooseCutoff = 'Choose the cutoff time';
  static const callSupport = 'Call support';
  static const closedMessage =
      'The cutoff for this date has passed (9 PM the evening before). '
      'Please call support for an emergency change.';

  static String skipDone(String date) => 'Skipped $date.';
  static String unskipDone(String date) => 'Skip removed for $date.';
  static String cutoffApplied(String date, String time) =>
      'Cutoff time for $date is now $time.';
  static const cutoffRequested = 'Change requested. Priveo will confirm it.';
  static const cannotOpenPhone = 'The phone could not be opened.';

  // Home.
  static const goodMorning = 'Good morning,';
  static const goodAfternoon = 'Good afternoon,';
  static const goodEvening = 'Good evening,';
  static const today = 'Today';
  static const tomorrow = 'Tomorrow';
  static const monthlyCheckIn = 'Monthly check-in';
  static const monthlyCheckInBody = 'Tell us how Priveo is doing this month.';
  static const crewHeading = 'Crew';

  // Default cutoff and interior day (SUB-08).
  static const editDefaults = 'Change cutoff time or interior day';
  static const defaultsTitle = 'Service defaults';
  static const interiorDayLabel = 'Interior care day';
  static const save = 'Save';
  static String defaultsSaved(String from) => 'Saved. It applies from $from.';
  static String defaultsFrozen(int n) => n == 1
      ? '1 planned date keeps the old cutoff time.'
      : '$n planned dates keep the old cutoff time.';
}
