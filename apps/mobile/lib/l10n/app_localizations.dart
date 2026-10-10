import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[Locale('en')];

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'Priveo'**
  String get appName;

  /// No description provided for @tagline.
  ///
  /// In en, this message translates to:
  /// **'Car care, at your doorstep'**
  String get tagline;

  /// No description provided for @loginTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get loginTitle;

  /// No description provided for @loginIdLabel.
  ///
  /// In en, this message translates to:
  /// **'Email, mobile or user ID'**
  String get loginIdLabel;

  /// No description provided for @passwordLabel.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get passwordLabel;

  /// No description provided for @showPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get showPassword;

  /// No description provided for @hidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get hidePassword;

  /// No description provided for @signInButton.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signInButton;

  /// No description provided for @signingIn.
  ///
  /// In en, this message translates to:
  /// **'Signing in'**
  String get signingIn;

  /// No description provided for @continueButton.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueButton;

  /// No description provided for @enterId.
  ///
  /// In en, this message translates to:
  /// **'Enter your email, mobile number or user ID.'**
  String get enterId;

  /// No description provided for @enterPassword.
  ///
  /// In en, this message translates to:
  /// **'Enter your password.'**
  String get enterPassword;

  /// No description provided for @termsNotice.
  ///
  /// In en, this message translates to:
  /// **'By continuing you accept the Terms and the Privacy Policy.'**
  String get termsNotice;

  /// No description provided for @changeId.
  ///
  /// In en, this message translates to:
  /// **'Change'**
  String get changeId;

  /// No description provided for @changeEmail.
  ///
  /// In en, this message translates to:
  /// **'Change email'**
  String get changeEmail;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get forgotPassword;

  /// No description provided for @codeTitle.
  ///
  /// In en, this message translates to:
  /// **'Enter the code'**
  String get codeTitle;

  /// No description provided for @codeSentTo.
  ///
  /// In en, this message translates to:
  /// **'We sent a 6-digit code to {email}. It works for 10 minutes.'**
  String codeSentTo(String email);

  /// No description provided for @codeLabel.
  ///
  /// In en, this message translates to:
  /// **'6-digit code'**
  String get codeLabel;

  /// No description provided for @enterCode.
  ///
  /// In en, this message translates to:
  /// **'Enter the 6-digit code.'**
  String get enterCode;

  /// No description provided for @verifyButton.
  ///
  /// In en, this message translates to:
  /// **'Verify'**
  String get verifyButton;

  /// No description provided for @resendIn.
  ///
  /// In en, this message translates to:
  /// **'Resend code in {time}'**
  String resendIn(String time);

  /// No description provided for @resendCode.
  ///
  /// In en, this message translates to:
  /// **'Resend code'**
  String get resendCode;

  /// No description provided for @newPasswordTitle.
  ///
  /// In en, this message translates to:
  /// **'Set a password'**
  String get newPasswordTitle;

  /// No description provided for @passwordRule.
  ///
  /// In en, this message translates to:
  /// **'Use at least 8 characters, with a letter and a number.'**
  String get passwordRule;

  /// No description provided for @newPasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'New password'**
  String get newPasswordLabel;

  /// No description provided for @confirmPasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get confirmPasswordLabel;

  /// No description provided for @passwordsDiffer.
  ///
  /// In en, this message translates to:
  /// **'The two passwords do not match.'**
  String get passwordsDiffer;

  /// No description provided for @savePassword.
  ///
  /// In en, this message translates to:
  /// **'Save and continue'**
  String get savePassword;

  /// No description provided for @networkError.
  ///
  /// In en, this message translates to:
  /// **'We could not reach the server. Check your connection and try again.'**
  String get networkError;

  /// No description provided for @demoAccounts.
  ///
  /// In en, this message translates to:
  /// **'Use demo account'**
  String get demoAccounts;

  /// No description provided for @signOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOut;

  /// No description provided for @comingSoon.
  ///
  /// In en, this message translates to:
  /// **'Coming soon'**
  String get comingSoon;

  /// No description provided for @tryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get tryAgain;

  /// No description provided for @loadFailed.
  ///
  /// In en, this message translates to:
  /// **'We could not load this screen.'**
  String get loadFailed;

  /// No description provided for @greeting.
  ///
  /// In en, this message translates to:
  /// **'Hello,'**
  String get greeting;

  /// No description provided for @quickActions.
  ///
  /// In en, this message translates to:
  /// **'Quick actions'**
  String get quickActions;

  /// No description provided for @viewCalendar.
  ///
  /// In en, this message translates to:
  /// **'View service calendar'**
  String get viewCalendar;

  /// No description provided for @nextService.
  ///
  /// In en, this message translates to:
  /// **'Next service'**
  String get nextService;

  /// No description provided for @notScheduledYet.
  ///
  /// In en, this message translates to:
  /// **'Not scheduled yet'**
  String get notScheduledYet;

  /// No description provided for @dailyCleanBy.
  ///
  /// In en, this message translates to:
  /// **'Daily clean by {time}'**
  String dailyCleanBy(String time);

  /// No description provided for @interiorCareOn.
  ///
  /// In en, this message translates to:
  /// **'Interior care on {day}'**
  String interiorCareOn(String day);

  /// No description provided for @noVehicles.
  ///
  /// In en, this message translates to:
  /// **'No vehicle is on your account yet. Contact Priveo.'**
  String get noVehicles;

  /// No description provided for @noRegistration.
  ///
  /// In en, this message translates to:
  /// **'Number to be added'**
  String get noRegistration;

  /// No description provided for @noParking.
  ///
  /// In en, this message translates to:
  /// **'Parking to be added'**
  String get noParking;

  /// No description provided for @noSubscription.
  ///
  /// In en, this message translates to:
  /// **'No subscription'**
  String get noSubscription;

  /// No description provided for @noPlan.
  ///
  /// In en, this message translates to:
  /// **'No plan'**
  String get noPlan;

  /// No description provided for @pricePerMonth.
  ///
  /// In en, this message translates to:
  /// **'{price} a month'**
  String pricePerMonth(String price);

  /// No description provided for @vehicleOf.
  ///
  /// In en, this message translates to:
  /// **'Vehicle {number} of {total}'**
  String vehicleOf(int number, int total);

  /// No description provided for @stepOf.
  ///
  /// In en, this message translates to:
  /// **'Step {number} of {total}'**
  String stepOf(int number, int total);

  /// No description provided for @onboardingIntro.
  ///
  /// In en, this message translates to:
  /// **'Check what we have, and fill in anything that is missing.'**
  String get onboardingIntro;

  /// No description provided for @reviewIntro.
  ///
  /// In en, this message translates to:
  /// **'Check everything once more, then confirm.'**
  String get reviewIntro;

  /// No description provided for @yourDetails.
  ///
  /// In en, this message translates to:
  /// **'Your details'**
  String get yourDetails;

  /// No description provided for @yourSociety.
  ///
  /// In en, this message translates to:
  /// **'Your society'**
  String get yourSociety;

  /// No description provided for @yourVehicle.
  ///
  /// In en, this message translates to:
  /// **'Your vehicle'**
  String get yourVehicle;

  /// No description provided for @reviewAndConfirm.
  ///
  /// In en, this message translates to:
  /// **'Review and confirm'**
  String get reviewAndConfirm;

  /// No description provided for @firstName.
  ///
  /// In en, this message translates to:
  /// **'First name'**
  String get firstName;

  /// No description provided for @lastName.
  ///
  /// In en, this message translates to:
  /// **'Last name'**
  String get lastName;

  /// No description provided for @name.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get name;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @mobileNumber.
  ///
  /// In en, this message translates to:
  /// **'Mobile number'**
  String get mobileNumber;

  /// No description provided for @society.
  ///
  /// In en, this message translates to:
  /// **'Society'**
  String get society;

  /// No description provided for @flat.
  ///
  /// In en, this message translates to:
  /// **'Flat'**
  String get flat;

  /// No description provided for @vehicle.
  ///
  /// In en, this message translates to:
  /// **'Vehicle'**
  String get vehicle;

  /// No description provided for @registration.
  ///
  /// In en, this message translates to:
  /// **'Registration'**
  String get registration;

  /// No description provided for @parking.
  ///
  /// In en, this message translates to:
  /// **'Parking'**
  String get parking;

  /// No description provided for @basement.
  ///
  /// In en, this message translates to:
  /// **'Basement'**
  String get basement;

  /// No description provided for @parkingNumber.
  ///
  /// In en, this message translates to:
  /// **'Parking number'**
  String get parkingNumber;

  /// No description provided for @parkingPreview.
  ///
  /// In en, this message translates to:
  /// **'Your spot: {spot}'**
  String parkingPreview(String spot);

  /// No description provided for @servicePreferences.
  ///
  /// In en, this message translates to:
  /// **'Service preferences'**
  String get servicePreferences;

  /// No description provided for @cutoffTime.
  ///
  /// In en, this message translates to:
  /// **'Service cutoff time'**
  String get cutoffTime;

  /// No description provided for @chooseTime.
  ///
  /// In en, this message translates to:
  /// **'Choose a time'**
  String get chooseTime;

  /// No description provided for @cutoffNote.
  ///
  /// In en, this message translates to:
  /// **'This is the time by which your daily clean will be done. Priveo assigns the exact slot.'**
  String get cutoffNote;

  /// No description provided for @interiorCareDay.
  ///
  /// In en, this message translates to:
  /// **'Interior care day'**
  String get interiorCareDay;

  /// No description provided for @plan.
  ///
  /// In en, this message translates to:
  /// **'Plan'**
  String get plan;

  /// No description provided for @yourPlan.
  ///
  /// In en, this message translates to:
  /// **'Your plan'**
  String get yourPlan;

  /// No description provided for @notOnFile.
  ///
  /// In en, this message translates to:
  /// **'Not on file'**
  String get notOnFile;

  /// No description provided for @onlyPriveoCanChange.
  ///
  /// In en, this message translates to:
  /// **'Only Priveo can change these. Contact support if something is wrong.'**
  String get onlyPriveoCanChange;

  /// No description provided for @enterFirstName.
  ///
  /// In en, this message translates to:
  /// **'Enter your first name, using letters only.'**
  String get enterFirstName;

  /// No description provided for @enterLastName.
  ///
  /// In en, this message translates to:
  /// **'Enter your last name, using letters only.'**
  String get enterLastName;

  /// No description provided for @enterMobile.
  ///
  /// In en, this message translates to:
  /// **'Enter a 10-digit mobile number.'**
  String get enterMobile;

  /// No description provided for @selectBasement.
  ///
  /// In en, this message translates to:
  /// **'Select the basement.'**
  String get selectBasement;

  /// No description provided for @enterParkingNumber.
  ///
  /// In en, this message translates to:
  /// **'Enter the parking number, in digits.'**
  String get enterParkingNumber;

  /// No description provided for @selectCutoff.
  ///
  /// In en, this message translates to:
  /// **'Please select your service cutoff time.'**
  String get selectCutoff;

  /// No description provided for @selectInteriorDay.
  ///
  /// In en, this message translates to:
  /// **'Please select your interior care day.'**
  String get selectInteriorDay;

  /// No description provided for @edit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get edit;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @confirmDetails.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get confirmDetails;

  /// No description provided for @subscription.
  ///
  /// In en, this message translates to:
  /// **'Subscription'**
  String get subscription;

  /// No description provided for @quickSkipPause.
  ///
  /// In en, this message translates to:
  /// **'Skip or Pause'**
  String get quickSkipPause;

  /// No description provided for @quickHistory.
  ///
  /// In en, this message translates to:
  /// **'Service History'**
  String get quickHistory;

  /// No description provided for @quickFeedback.
  ///
  /// In en, this message translates to:
  /// **'Give Feedback'**
  String get quickFeedback;

  /// No description provided for @quickReportIssue.
  ///
  /// In en, this message translates to:
  /// **'Report an Issue'**
  String get quickReportIssue;

  /// No description provided for @tabHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get tabHome;

  /// No description provided for @tabCalendar.
  ///
  /// In en, this message translates to:
  /// **'Calendar'**
  String get tabCalendar;

  /// No description provided for @tabAccount.
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get tabAccount;

  /// No description provided for @tabSupport.
  ///
  /// In en, this message translates to:
  /// **'Support'**
  String get tabSupport;

  /// No description provided for @crewToday.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get crewToday;

  /// No description provided for @crewTotal.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get crewTotal;

  /// No description provided for @crewDone.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get crewDone;

  /// No description provided for @crewLeft.
  ///
  /// In en, this message translates to:
  /// **'Left'**
  String get crewLeft;

  /// No description provided for @adminAlerts.
  ///
  /// In en, this message translates to:
  /// **'Alerts'**
  String get adminAlerts;

  /// No description provided for @adminNeedsScheduling.
  ///
  /// In en, this message translates to:
  /// **'Needs scheduling'**
  String get adminNeedsScheduling;

  /// No description provided for @adminPaymentsToConfirm.
  ///
  /// In en, this message translates to:
  /// **'Payments to confirm'**
  String get adminPaymentsToConfirm;

  /// No description provided for @adminNoPayments.
  ///
  /// In en, this message translates to:
  /// **'No payments waiting.'**
  String get adminNoPayments;

  /// No description provided for @demoCustomer.
  ///
  /// In en, this message translates to:
  /// **'Customer'**
  String get demoCustomer;

  /// No description provided for @demoCrew.
  ///
  /// In en, this message translates to:
  /// **'Crew'**
  String get demoCrew;

  /// No description provided for @demoAdmin.
  ///
  /// In en, this message translates to:
  /// **'Admin'**
  String get demoAdmin;

  /// No description provided for @signOutAll.
  ///
  /// In en, this message translates to:
  /// **'Sign out of all devices'**
  String get signOutAll;

  /// No description provided for @signOutAllBody.
  ///
  /// In en, this message translates to:
  /// **'This signs you out on every phone and browser, including this one.'**
  String get signOutAllBody;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
