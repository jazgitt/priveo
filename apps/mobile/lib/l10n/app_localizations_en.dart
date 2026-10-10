// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Priveo';

  @override
  String get tagline => 'Car care, at your doorstep';

  @override
  String get loginTitle => 'Sign in';

  @override
  String get loginIdLabel => 'Email, mobile or user ID';

  @override
  String get passwordLabel => 'Password';

  @override
  String get showPassword => 'Show password';

  @override
  String get hidePassword => 'Hide password';

  @override
  String get signInButton => 'Sign in';

  @override
  String get signingIn => 'Signing in';

  @override
  String get continueButton => 'Continue';

  @override
  String get enterId => 'Enter your email, mobile number or user ID.';

  @override
  String get enterPassword => 'Enter your password.';

  @override
  String get termsNotice =>
      'By continuing you accept the Terms and the Privacy Policy.';

  @override
  String get changeId => 'Change';

  @override
  String get changeEmail => 'Change email';

  @override
  String get forgotPassword => 'Forgot password?';

  @override
  String get codeTitle => 'Enter the code';

  @override
  String codeSentTo(String email) {
    return 'We sent a 6-digit code to $email. It works for 10 minutes.';
  }

  @override
  String get codeLabel => '6-digit code';

  @override
  String get enterCode => 'Enter the 6-digit code.';

  @override
  String get verifyButton => 'Verify';

  @override
  String resendIn(String time) {
    return 'Resend code in $time';
  }

  @override
  String get resendCode => 'Resend code';

  @override
  String get newPasswordTitle => 'Set a password';

  @override
  String get passwordRule =>
      'Use at least 8 characters, with a letter and a number.';

  @override
  String get newPasswordLabel => 'New password';

  @override
  String get confirmPasswordLabel => 'Confirm password';

  @override
  String get passwordsDiffer => 'The two passwords do not match.';

  @override
  String get savePassword => 'Save and continue';

  @override
  String get networkError =>
      'We could not reach the server. Check your connection and try again.';

  @override
  String get demoAccounts => 'Use demo account';

  @override
  String get signOut => 'Sign out';

  @override
  String get comingSoon => 'Coming soon';

  @override
  String get tryAgain => 'Try again';

  @override
  String get loadFailed => 'We could not load this screen.';

  @override
  String get greeting => 'Hello,';

  @override
  String get quickActions => 'Quick actions';

  @override
  String get viewCalendar => 'View service calendar';

  @override
  String get nextService => 'Next service';

  @override
  String get notScheduledYet => 'Not scheduled yet';

  @override
  String dailyCleanBy(String time) {
    return 'Daily clean by $time';
  }

  @override
  String interiorCareOn(String day) {
    return 'Interior care on $day';
  }

  @override
  String get noVehicles => 'No vehicle is on your account yet. Contact Priveo.';

  @override
  String get noRegistration => 'Number to be added';

  @override
  String get noParking => 'Parking to be added';

  @override
  String get noSubscription => 'No subscription';

  @override
  String get noPlan => 'No plan';

  @override
  String pricePerMonth(String price) {
    return '$price a month';
  }

  @override
  String vehicleOf(int number, int total) {
    return 'Vehicle $number of $total';
  }

  @override
  String stepOf(int number, int total) {
    return 'Step $number of $total';
  }

  @override
  String get onboardingIntro =>
      'Check what we have, and fill in anything that is missing.';

  @override
  String get reviewIntro => 'Check everything once more, then confirm.';

  @override
  String get yourDetails => 'Your details';

  @override
  String get yourSociety => 'Your society';

  @override
  String get yourVehicle => 'Your vehicle';

  @override
  String get reviewAndConfirm => 'Review and confirm';

  @override
  String get firstName => 'First name';

  @override
  String get lastName => 'Last name';

  @override
  String get name => 'Name';

  @override
  String get email => 'Email';

  @override
  String get mobileNumber => 'Mobile number';

  @override
  String get society => 'Society';

  @override
  String get flat => 'Flat';

  @override
  String get vehicle => 'Vehicle';

  @override
  String get registration => 'Registration';

  @override
  String get parking => 'Parking';

  @override
  String get basement => 'Basement';

  @override
  String get parkingNumber => 'Parking number';

  @override
  String parkingPreview(String spot) {
    return 'Your spot: $spot';
  }

  @override
  String get servicePreferences => 'Service preferences';

  @override
  String get cutoffTime => 'Service cutoff time';

  @override
  String get chooseTime => 'Choose a time';

  @override
  String get cutoffNote =>
      'This is the time by which your daily clean will be done. Priveo assigns the exact slot.';

  @override
  String get interiorCareDay => 'Interior care day';

  @override
  String get plan => 'Plan';

  @override
  String get yourPlan => 'Your plan';

  @override
  String get notOnFile => 'Not on file';

  @override
  String get onlyPriveoCanChange =>
      'Only Priveo can change these. Contact support if something is wrong.';

  @override
  String get enterFirstName => 'Enter your first name, using letters only.';

  @override
  String get enterLastName => 'Enter your last name, using letters only.';

  @override
  String get enterMobile => 'Enter a 10-digit mobile number.';

  @override
  String get selectBasement => 'Select the basement.';

  @override
  String get enterParkingNumber => 'Enter the parking number, in digits.';

  @override
  String get selectCutoff => 'Please select your service cutoff time.';

  @override
  String get selectInteriorDay => 'Please select your interior care day.';

  @override
  String get edit => 'Edit';

  @override
  String get back => 'Back';

  @override
  String get confirmDetails => 'Confirm';

  @override
  String get subscription => 'Subscription';

  @override
  String get quickSkipPause => 'Skip or Pause';

  @override
  String get quickHistory => 'Service History';

  @override
  String get quickFeedback => 'Give Feedback';

  @override
  String get quickReportIssue => 'Report an Issue';

  @override
  String get tabHome => 'Home';

  @override
  String get tabCalendar => 'Calendar';

  @override
  String get tabAccount => 'Account';

  @override
  String get tabSupport => 'Support';

  @override
  String get crewToday => 'Today';

  @override
  String get crewTotal => 'Total';

  @override
  String get crewDone => 'Done';

  @override
  String get crewLeft => 'Left';

  @override
  String get adminAlerts => 'Alerts';

  @override
  String get adminNeedsScheduling => 'Needs scheduling';

  @override
  String get adminPaymentsToConfirm => 'Payments to confirm';

  @override
  String get adminNoPayments => 'No payments waiting.';

  @override
  String get demoCustomer => 'Customer';

  @override
  String get demoCrew => 'Crew';

  @override
  String get demoAdmin => 'Admin';

  @override
  String get signOutAll => 'Sign out of all devices';

  @override
  String get signOutAllBody =>
      'This signs you out on every phone and browser, including this one.';

  @override
  String get cancel => 'Cancel';
}
