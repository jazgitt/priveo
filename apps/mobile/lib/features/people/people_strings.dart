/// English text for the people screens. The same keys and words are in
/// `lib/l10n/fragments/people.arb`. Until that file is merged into
/// `app_en.arb` and the localisations are regenerated, the screens read them
/// from here; then this class is replaced by `AppLocalizations`.
class PeopleStrings {
  const PeopleStrings();

  static const instance = PeopleStrings();

  String get crewProfileTitle => 'My profile';
  String get role => 'Role';
  String get workingHours => 'Working hours';
  String get dayOff => 'Off';
  String hoursRange(String start, String end) => '$start to $end';
  String get profileNote =>
      'Your name, mobile number, society and role are set by Priveo.';
  String get profileMissing =>
      'Your details are not set up yet. Contact Priveo.';
  String get vehiclesTitle => 'My vehicles';
  String get vehicleDetails => 'Vehicle details';
  String get subscriptionStatus => 'Subscription status';
  String get monthlyAmount => 'Monthly amount';
  String get vehicleNotFound => 'This vehicle is not on your account.';
}
