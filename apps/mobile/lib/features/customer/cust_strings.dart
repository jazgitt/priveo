/// English text of the customer slice. The same keys, in snake case with the
/// `cust_` prefix, are in `lib/l10n/fragments/customer.arb`; at integration
/// the fragment is merged into `app_en.arb` and these move to
/// `AppLocalizations`.
class CustStrings {
  const CustStrings._();

  static const calendarTitle = 'Service calendar';
  static const previousMonth = 'Previous month';
  static const nextMonth = 'Next month';
  static const legendDone = 'Completed';
  static const legendInterior = 'Exterior + Interior';
  static const legendSpa = 'Deep Spa';
  static const legendScheduled = 'Scheduled';
  static const legendSkipped = 'Skipped';
  static const legendMissed = 'Missed';
  static const noVisit = 'No visit on this day.';
  static const noVisitChip = 'No visit';
  static const viewDetails = 'View service details';
  static const proofAfterVisit = 'Proof appears after the visit.';
  static const youSkipped = 'You skipped this date.';
  static const missedNote = 'This service was missed.';

  static String scheduledBy(String time) =>
      'Scheduled to be completed by $time. $proofAfterVisit';

  static const historyTitle = 'Service history';
  static const historyEmpty = 'No services yet.';

  static String photoCount(int n) => n == 1 ? '1 photo' : '$n photos';

  static const visitTitle = 'Service details';
  static const jobsHeading = 'Jobs';
  static const photosHeading = 'Photos';
  static const videosHeading = 'Videos';
  static const noProofYet =
      'Photos and videos appear once the service is done.';
  static const playVideo = 'Play video';
  static const photoUnavailable = 'Photo unavailable';
  static const close = 'Close';

  static String photoPosition(int i, int n) => '$i / $n';

  static const vehiclesTitle = 'My vehicles';
  static const vehiclesEmpty = 'No vehicles yet.';
  static const noSubscription = 'No subscription';
  static const numberToBeAdded = 'Number to be added';
  static const vehicleTitle = 'Vehicle';
  static const fieldRegistration = 'Registration';
  static const fieldCar = 'Make and model';
  static const fieldVariant = 'Variant';
  static const fieldCategory = 'Category';
  static const fieldSociety = 'Society';
  static const fieldParking = 'Parking';
  static const fieldPlan = 'Plan';
  static const fieldCutoff = 'Service cutoff time';
  static const fieldInteriorDay = 'Interior care day';
  static const notOnFile = 'Not on file';
  static const carDetailsViaSupport =
      'Car details change only through Priveo support.';

  static const accountTitle = 'My account';
  static const accountVehicles = 'My vehicles';
  static const accountHistory = 'Service history';
  static const accountNotifications = 'Notifications';
  static const accountSignOut = 'Sign out';
  static const settingsHeading = 'Settings';
  static const settingsNote =
      'Notification choices will be available in a later update.';
  static const settingsNotifications = 'Notifications';
  static const settingsIntro =
      'Choose which messages Priveo sends you. All are on to start.';
  static const settingsSaveFailed =
      'Could not save this choice. Please try again.';
  static const accountSettings = 'Notification settings';
  static const settingsUsageHeading = 'Usage data';
  static const settingsUsageTitle = 'Share usage data';
  static const settingsUsageHelp =
      'Helps us find and fix problems. Includes the screens you see in the app.';

  static const notificationsTitle = 'Notifications';
  static const notificationsEmpty = 'No notifications yet.';
  static const markAllRead = 'Mark all as read';

  static const nextServiceHeading = 'Next service';
}
