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

  /// No description provided for @cust_calendar_title.
  ///
  /// In en, this message translates to:
  /// **'Service calendar'**
  String get cust_calendar_title;

  /// No description provided for @cust_previous_month.
  ///
  /// In en, this message translates to:
  /// **'Previous month'**
  String get cust_previous_month;

  /// No description provided for @cust_next_month.
  ///
  /// In en, this message translates to:
  /// **'Next month'**
  String get cust_next_month;

  /// No description provided for @cust_legend_done.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get cust_legend_done;

  /// No description provided for @cust_legend_interior.
  ///
  /// In en, this message translates to:
  /// **'Exterior + Interior'**
  String get cust_legend_interior;

  /// No description provided for @cust_legend_spa.
  ///
  /// In en, this message translates to:
  /// **'Deep Spa'**
  String get cust_legend_spa;

  /// No description provided for @cust_legend_scheduled.
  ///
  /// In en, this message translates to:
  /// **'Scheduled'**
  String get cust_legend_scheduled;

  /// No description provided for @cust_legend_skipped.
  ///
  /// In en, this message translates to:
  /// **'Skipped'**
  String get cust_legend_skipped;

  /// No description provided for @cust_legend_missed.
  ///
  /// In en, this message translates to:
  /// **'Missed'**
  String get cust_legend_missed;

  /// No description provided for @cust_no_visit.
  ///
  /// In en, this message translates to:
  /// **'No visit on this day.'**
  String get cust_no_visit;

  /// No description provided for @cust_no_visit_chip.
  ///
  /// In en, this message translates to:
  /// **'No visit'**
  String get cust_no_visit_chip;

  /// No description provided for @cust_view_details.
  ///
  /// In en, this message translates to:
  /// **'View service details'**
  String get cust_view_details;

  /// No description provided for @cust_proof_after_visit.
  ///
  /// In en, this message translates to:
  /// **'Proof appears after the visit.'**
  String get cust_proof_after_visit;

  /// No description provided for @cust_you_skipped.
  ///
  /// In en, this message translates to:
  /// **'You skipped this date.'**
  String get cust_you_skipped;

  /// No description provided for @cust_missed_note.
  ///
  /// In en, this message translates to:
  /// **'This service was missed.'**
  String get cust_missed_note;

  /// No description provided for @cust_scheduled_by.
  ///
  /// In en, this message translates to:
  /// **'Scheduled to be completed by {time}. Proof appears after the visit.'**
  String cust_scheduled_by(String time);

  /// No description provided for @cust_history_title.
  ///
  /// In en, this message translates to:
  /// **'Service history'**
  String get cust_history_title;

  /// No description provided for @cust_history_empty.
  ///
  /// In en, this message translates to:
  /// **'No services yet.'**
  String get cust_history_empty;

  /// No description provided for @cust_photo_count.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 photo} other{{count} photos}}'**
  String cust_photo_count(int count);

  /// No description provided for @cust_visit_title.
  ///
  /// In en, this message translates to:
  /// **'Service details'**
  String get cust_visit_title;

  /// No description provided for @cust_jobs_heading.
  ///
  /// In en, this message translates to:
  /// **'Jobs'**
  String get cust_jobs_heading;

  /// No description provided for @cust_photos_heading.
  ///
  /// In en, this message translates to:
  /// **'Photos'**
  String get cust_photos_heading;

  /// No description provided for @cust_videos_heading.
  ///
  /// In en, this message translates to:
  /// **'Videos'**
  String get cust_videos_heading;

  /// No description provided for @cust_no_proof_yet.
  ///
  /// In en, this message translates to:
  /// **'Photos and videos appear once the service is done.'**
  String get cust_no_proof_yet;

  /// No description provided for @cust_play_video.
  ///
  /// In en, this message translates to:
  /// **'Play video'**
  String get cust_play_video;

  /// No description provided for @cust_photo_unavailable.
  ///
  /// In en, this message translates to:
  /// **'Photo unavailable'**
  String get cust_photo_unavailable;

  /// No description provided for @cust_close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get cust_close;

  /// No description provided for @cust_photo_position.
  ///
  /// In en, this message translates to:
  /// **'{index} / {total}'**
  String cust_photo_position(int index, int total);

  /// No description provided for @cust_vehicles_title.
  ///
  /// In en, this message translates to:
  /// **'My vehicles'**
  String get cust_vehicles_title;

  /// No description provided for @cust_vehicles_empty.
  ///
  /// In en, this message translates to:
  /// **'No vehicles yet.'**
  String get cust_vehicles_empty;

  /// No description provided for @cust_no_subscription.
  ///
  /// In en, this message translates to:
  /// **'No subscription'**
  String get cust_no_subscription;

  /// No description provided for @cust_number_to_be_added.
  ///
  /// In en, this message translates to:
  /// **'Number to be added'**
  String get cust_number_to_be_added;

  /// No description provided for @cust_vehicle_title.
  ///
  /// In en, this message translates to:
  /// **'Vehicle'**
  String get cust_vehicle_title;

  /// No description provided for @cust_field_registration.
  ///
  /// In en, this message translates to:
  /// **'Registration'**
  String get cust_field_registration;

  /// No description provided for @cust_field_car.
  ///
  /// In en, this message translates to:
  /// **'Make and model'**
  String get cust_field_car;

  /// No description provided for @cust_field_variant.
  ///
  /// In en, this message translates to:
  /// **'Variant'**
  String get cust_field_variant;

  /// No description provided for @cust_field_category.
  ///
  /// In en, this message translates to:
  /// **'Category'**
  String get cust_field_category;

  /// No description provided for @cust_field_society.
  ///
  /// In en, this message translates to:
  /// **'Society'**
  String get cust_field_society;

  /// No description provided for @cust_field_parking.
  ///
  /// In en, this message translates to:
  /// **'Parking'**
  String get cust_field_parking;

  /// No description provided for @cust_field_plan.
  ///
  /// In en, this message translates to:
  /// **'Plan'**
  String get cust_field_plan;

  /// No description provided for @cust_field_cutoff.
  ///
  /// In en, this message translates to:
  /// **'Service cutoff time'**
  String get cust_field_cutoff;

  /// No description provided for @cust_field_interior_day.
  ///
  /// In en, this message translates to:
  /// **'Interior care day'**
  String get cust_field_interior_day;

  /// No description provided for @cust_not_on_file.
  ///
  /// In en, this message translates to:
  /// **'Not on file'**
  String get cust_not_on_file;

  /// No description provided for @cust_car_details_via_support.
  ///
  /// In en, this message translates to:
  /// **'Car details change only through Priveo support.'**
  String get cust_car_details_via_support;

  /// No description provided for @cust_account_title.
  ///
  /// In en, this message translates to:
  /// **'My account'**
  String get cust_account_title;

  /// No description provided for @cust_account_vehicles.
  ///
  /// In en, this message translates to:
  /// **'My vehicles'**
  String get cust_account_vehicles;

  /// No description provided for @cust_account_history.
  ///
  /// In en, this message translates to:
  /// **'Service history'**
  String get cust_account_history;

  /// No description provided for @cust_account_notifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get cust_account_notifications;

  /// No description provided for @cust_account_sign_out.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get cust_account_sign_out;

  /// No description provided for @cust_settings_heading.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get cust_settings_heading;

  /// No description provided for @cust_settings_note.
  ///
  /// In en, this message translates to:
  /// **'Notification choices will be available in a later update.'**
  String get cust_settings_note;

  /// No description provided for @cust_notifications_title.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get cust_notifications_title;

  /// No description provided for @cust_notifications_empty.
  ///
  /// In en, this message translates to:
  /// **'No notifications yet.'**
  String get cust_notifications_empty;

  /// No description provided for @cust_mark_all_read.
  ///
  /// In en, this message translates to:
  /// **'Mark all as read'**
  String get cust_mark_all_read;

  /// No description provided for @cust_next_service_heading.
  ///
  /// In en, this message translates to:
  /// **'Next service'**
  String get cust_next_service_heading;

  /// No description provided for @people_crewProfileTitle.
  ///
  /// In en, this message translates to:
  /// **'My profile'**
  String get people_crewProfileTitle;

  /// No description provided for @people_role.
  ///
  /// In en, this message translates to:
  /// **'Role'**
  String get people_role;

  /// No description provided for @people_workingHours.
  ///
  /// In en, this message translates to:
  /// **'Working hours'**
  String get people_workingHours;

  /// No description provided for @people_dayOff.
  ///
  /// In en, this message translates to:
  /// **'Off'**
  String get people_dayOff;

  /// No description provided for @people_hoursRange.
  ///
  /// In en, this message translates to:
  /// **'{start} to {end}'**
  String people_hoursRange(String start, String end);

  /// No description provided for @people_profileNote.
  ///
  /// In en, this message translates to:
  /// **'Your name, mobile number, society and role are set by Priveo.'**
  String get people_profileNote;

  /// No description provided for @people_profileMissing.
  ///
  /// In en, this message translates to:
  /// **'Your details are not set up yet. Contact Priveo.'**
  String get people_profileMissing;

  /// No description provided for @people_vehiclesTitle.
  ///
  /// In en, this message translates to:
  /// **'My vehicles'**
  String get people_vehiclesTitle;

  /// No description provided for @people_vehicleDetails.
  ///
  /// In en, this message translates to:
  /// **'Vehicle details'**
  String get people_vehicleDetails;

  /// No description provided for @people_subscriptionStatus.
  ///
  /// In en, this message translates to:
  /// **'Subscription status'**
  String get people_subscriptionStatus;

  /// No description provided for @people_monthlyAmount.
  ///
  /// In en, this message translates to:
  /// **'Monthly amount'**
  String get people_monthlyAmount;

  /// No description provided for @people_vehicleNotFound.
  ///
  /// In en, this message translates to:
  /// **'This vehicle is not on your account.'**
  String get people_vehicleNotFound;

  /// No description provided for @support_title.
  ///
  /// In en, this message translates to:
  /// **'Help and support'**
  String get support_title;

  /// No description provided for @support_call.
  ///
  /// In en, this message translates to:
  /// **'Call support'**
  String get support_call;

  /// No description provided for @support_whatsapp.
  ///
  /// In en, this message translates to:
  /// **'WhatsApp support'**
  String get support_whatsapp;

  /// No description provided for @support_hours.
  ///
  /// In en, this message translates to:
  /// **'Support hours: {hours}'**
  String support_hours(String hours);

  /// No description provided for @support_report_issue.
  ///
  /// In en, this message translates to:
  /// **'Report an issue'**
  String get support_report_issue;

  /// No description provided for @support_my_complaints.
  ///
  /// In en, this message translates to:
  /// **'My complaints'**
  String get support_my_complaints;

  /// No description provided for @support_complaints_in_progress.
  ///
  /// In en, this message translates to:
  /// **'{count} in progress'**
  String support_complaints_in_progress(String count);

  /// No description provided for @support_give_feedback.
  ///
  /// In en, this message translates to:
  /// **'Give feedback'**
  String get support_give_feedback;

  /// No description provided for @support_monthly_checkin.
  ///
  /// In en, this message translates to:
  /// **'Monthly check-in'**
  String get support_monthly_checkin;

  /// No description provided for @support_cannot_open.
  ///
  /// In en, this message translates to:
  /// **'We could not open that. Please try again.'**
  String get support_cannot_open;

  /// No description provided for @support_report_title.
  ///
  /// In en, this message translates to:
  /// **'Report an issue'**
  String get support_report_title;

  /// No description provided for @support_issue_category.
  ///
  /// In en, this message translates to:
  /// **'What went wrong?'**
  String get support_issue_category;

  /// No description provided for @support_issue_choose.
  ///
  /// In en, this message translates to:
  /// **'Choose what went wrong.'**
  String get support_issue_choose;

  /// No description provided for @support_issue_linked_visit.
  ///
  /// In en, this message translates to:
  /// **'This report is linked to the clean you came from.'**
  String get support_issue_linked_visit;

  /// No description provided for @support_issue_description.
  ///
  /// In en, this message translates to:
  /// **'Describe what happened'**
  String get support_issue_description;

  /// No description provided for @support_issue_description_required.
  ///
  /// In en, this message translates to:
  /// **'Describe what happened.'**
  String get support_issue_description_required;

  /// No description provided for @support_issue_send.
  ///
  /// In en, this message translates to:
  /// **'Send report'**
  String get support_issue_send;

  /// No description provided for @support_issue_sent.
  ///
  /// In en, this message translates to:
  /// **'Thank you. We will reply within 4 hours.'**
  String get support_issue_sent;

  /// No description provided for @support_complaints_title.
  ///
  /// In en, this message translates to:
  /// **'My complaints'**
  String get support_complaints_title;

  /// No description provided for @support_complaints_empty.
  ///
  /// In en, this message translates to:
  /// **'You have not raised any complaints.'**
  String get support_complaints_empty;

  /// No description provided for @support_complaint_raised_on.
  ///
  /// In en, this message translates to:
  /// **'Raised {date}'**
  String support_complaint_raised_on(String date);

  /// No description provided for @support_complaint_reply_hint.
  ///
  /// In en, this message translates to:
  /// **'Write a reply'**
  String get support_complaint_reply_hint;

  /// No description provided for @support_complaint_send.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get support_complaint_send;

  /// No description provided for @support_complaint_resolved.
  ///
  /// In en, this message translates to:
  /// **'This complaint is resolved. Raise a new one if the problem is back.'**
  String get support_complaint_resolved;

  /// No description provided for @support_thread_you.
  ///
  /// In en, this message translates to:
  /// **'You'**
  String get support_thread_you;

  /// No description provided for @support_thread_priveo.
  ///
  /// In en, this message translates to:
  /// **'Priveo'**
  String get support_thread_priveo;

  /// No description provided for @support_status_changed.
  ///
  /// In en, this message translates to:
  /// **'Status: {status}'**
  String support_status_changed(String status);

  /// No description provided for @support_feedback_title.
  ///
  /// In en, this message translates to:
  /// **'Give feedback'**
  String get support_feedback_title;

  /// No description provided for @support_feedback_category.
  ///
  /// In en, this message translates to:
  /// **'What is it about? (optional)'**
  String get support_feedback_category;

  /// No description provided for @support_feedback_rating.
  ///
  /// In en, this message translates to:
  /// **'Your rating'**
  String get support_feedback_rating;

  /// No description provided for @support_feedback_comment.
  ///
  /// In en, this message translates to:
  /// **'Comments'**
  String get support_feedback_comment;

  /// No description provided for @support_feedback_testimonial.
  ///
  /// In en, this message translates to:
  /// **'Priveo may quote my feedback as a testimonial.'**
  String get support_feedback_testimonial;

  /// No description provided for @support_feedback_send.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get support_feedback_send;

  /// No description provided for @support_feedback_thanks.
  ///
  /// In en, this message translates to:
  /// **'Thank you for your feedback.'**
  String get support_feedback_thanks;

  /// No description provided for @support_star.
  ///
  /// In en, this message translates to:
  /// **'Rate {n} out of 5'**
  String support_star(String n);

  /// No description provided for @support_rate_title.
  ///
  /// In en, this message translates to:
  /// **'Rate this clean'**
  String get support_rate_title;

  /// No description provided for @support_rate_positive_tags.
  ///
  /// In en, this message translates to:
  /// **'What went well? (optional)'**
  String get support_rate_positive_tags;

  /// No description provided for @support_rate_issue_tags.
  ///
  /// In en, this message translates to:
  /// **'What could be better? (optional)'**
  String get support_rate_issue_tags;

  /// No description provided for @support_rate_thanks.
  ///
  /// In en, this message translates to:
  /// **'Thank you for rating this clean.'**
  String get support_rate_thanks;

  /// No description provided for @support_checkin_title.
  ///
  /// In en, this message translates to:
  /// **'Monthly check-in'**
  String get support_checkin_title;

  /// No description provided for @support_checkin_intro.
  ///
  /// In en, this message translates to:
  /// **'How is Priveo doing for {vehicle}? Tap a star for any of these.'**
  String support_checkin_intro(String vehicle);

  /// No description provided for @support_checkin_comment.
  ///
  /// In en, this message translates to:
  /// **'Anything else? (optional)'**
  String get support_checkin_comment;

  /// No description provided for @support_checkin_submit.
  ///
  /// In en, this message translates to:
  /// **'Submit'**
  String get support_checkin_submit;

  /// No description provided for @support_checkin_thanks.
  ///
  /// In en, this message translates to:
  /// **'Thank you. Your check-in is saved.'**
  String get support_checkin_thanks;

  /// No description provided for @support_checkin_none.
  ///
  /// In en, this message translates to:
  /// **'There is no check-in to give right now.'**
  String get support_checkin_none;

  /// No description provided for @support_crew_ratings_title.
  ///
  /// In en, this message translates to:
  /// **'Ratings'**
  String get support_crew_ratings_title;

  /// No description provided for @support_crew_ratings_note.
  ///
  /// In en, this message translates to:
  /// **'Customers rate each visit as a whole. A rating is never given to a crew member.'**
  String get support_crew_ratings_note;

  /// No description provided for @support_crew_ratings_average.
  ///
  /// In en, this message translates to:
  /// **'Average rating'**
  String get support_crew_ratings_average;

  /// No description provided for @support_crew_ratings_count.
  ///
  /// In en, this message translates to:
  /// **'{count} ratings in the last {days} days'**
  String support_crew_ratings_count(String count, String days);

  /// No description provided for @support_crew_ratings_none.
  ///
  /// In en, this message translates to:
  /// **'No ratings yet.'**
  String get support_crew_ratings_none;

  /// No description provided for @support_alerts_title.
  ///
  /// In en, this message translates to:
  /// **'Alerts'**
  String get support_alerts_title;

  /// No description provided for @support_alerts_unread.
  ///
  /// In en, this message translates to:
  /// **'{count} unread'**
  String support_alerts_unread(String count);

  /// No description provided for @support_alerts_empty.
  ///
  /// In en, this message translates to:
  /// **'No alerts.'**
  String get support_alerts_empty;

  /// No description provided for @support_alerts_mark_all.
  ///
  /// In en, this message translates to:
  /// **'Mark all as read'**
  String get support_alerts_mark_all;

  /// No description provided for @crew_offline.
  ///
  /// In en, this message translates to:
  /// **'Could not reach Priveo. Check the connection and try again.'**
  String get crew_offline;

  /// No description provided for @crew_team.
  ///
  /// In en, this message translates to:
  /// **'Team'**
  String get crew_team;

  /// No description provided for @crew_profile.
  ///
  /// In en, this message translates to:
  /// **'My profile'**
  String get crew_profile;

  /// No description provided for @crew_all_jobs.
  ///
  /// In en, this message translates to:
  /// **'All jobs'**
  String get crew_all_jobs;

  /// No description provided for @crew_all.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get crew_all;

  /// No description provided for @crew_previous_day.
  ///
  /// In en, this message translates to:
  /// **'Previous day'**
  String get crew_previous_day;

  /// No description provided for @crew_next_day.
  ///
  /// In en, this message translates to:
  /// **'Next day'**
  String get crew_next_day;

  /// No description provided for @crew_no_jobs.
  ///
  /// In en, this message translates to:
  /// **'No jobs for this day.'**
  String get crew_no_jobs;

  /// No description provided for @crew_job_title.
  ///
  /// In en, this message translates to:
  /// **'Job'**
  String get crew_job_title;

  /// No description provided for @crew_start_job.
  ///
  /// In en, this message translates to:
  /// **'Start job'**
  String get crew_start_job;

  /// No description provided for @crew_continue_job.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get crew_continue_job;

  /// No description provided for @crew_could_not_complete.
  ///
  /// In en, this message translates to:
  /// **'Could not complete'**
  String get crew_could_not_complete;

  /// No description provided for @crew_service.
  ///
  /// In en, this message translates to:
  /// **'Service'**
  String get crew_service;

  /// No description provided for @crew_car.
  ///
  /// In en, this message translates to:
  /// **'Car'**
  String get crew_car;

  /// No description provided for @crew_category.
  ///
  /// In en, this message translates to:
  /// **'Category'**
  String get crew_category;

  /// No description provided for @crew_society.
  ///
  /// In en, this message translates to:
  /// **'Society'**
  String get crew_society;

  /// No description provided for @crew_parking.
  ///
  /// In en, this message translates to:
  /// **'Parking'**
  String get crew_parking;

  /// No description provided for @crew_finish_by_label.
  ///
  /// In en, this message translates to:
  /// **'Finish by'**
  String get crew_finish_by_label;

  /// No description provided for @crew_slot.
  ///
  /// In en, this message translates to:
  /// **'Slot'**
  String get crew_slot;

  /// No description provided for @crew_date.
  ///
  /// In en, this message translates to:
  /// **'Date'**
  String get crew_date;

  /// No description provided for @crew_checklist.
  ///
  /// In en, this message translates to:
  /// **'Checklist'**
  String get crew_checklist;

  /// No description provided for @crew_assigned_to.
  ///
  /// In en, this message translates to:
  /// **'Assigned to'**
  String get crew_assigned_to;

  /// No description provided for @crew_skipped_by_manager.
  ///
  /// In en, this message translates to:
  /// **'Skipped by a Manager'**
  String get crew_skipped_by_manager;

  /// No description provided for @crew_perform_title.
  ///
  /// In en, this message translates to:
  /// **'Perform service'**
  String get crew_perform_title;

  /// No description provided for @crew_proof.
  ///
  /// In en, this message translates to:
  /// **'Photos and video'**
  String get crew_proof;

  /// No description provided for @crew_take_photo.
  ///
  /// In en, this message translates to:
  /// **'Take photo'**
  String get crew_take_photo;

  /// No description provided for @crew_choose_photo.
  ///
  /// In en, this message translates to:
  /// **'Choose photo'**
  String get crew_choose_photo;

  /// No description provided for @crew_record_video.
  ///
  /// In en, this message translates to:
  /// **'Record video'**
  String get crew_record_video;

  /// No description provided for @crew_choose_video.
  ///
  /// In en, this message translates to:
  /// **'Choose video'**
  String get crew_choose_video;

  /// No description provided for @crew_format_not_accepted.
  ///
  /// In en, this message translates to:
  /// **'This file format is not accepted.'**
  String get crew_format_not_accepted;

  /// No description provided for @crew_photo_too_large.
  ///
  /// In en, this message translates to:
  /// **'A photo must be under 10 MB.'**
  String get crew_photo_too_large;

  /// No description provided for @crew_video_too_large.
  ///
  /// In en, this message translates to:
  /// **'A video must be under 25 MB.'**
  String get crew_video_too_large;

  /// No description provided for @crew_added_to_queue.
  ///
  /// In en, this message translates to:
  /// **'Saved. It will upload when there is a connection.'**
  String get crew_added_to_queue;

  /// No description provided for @crew_capture_failed.
  ///
  /// In en, this message translates to:
  /// **'Could not get the file. Please try again.'**
  String get crew_capture_failed;

  /// No description provided for @crew_job_completed.
  ///
  /// In en, this message translates to:
  /// **'Job completed.'**
  String get crew_job_completed;

  /// No description provided for @crew_mark_complete.
  ///
  /// In en, this message translates to:
  /// **'Mark complete'**
  String get crew_mark_complete;

  /// No description provided for @crew_before_complete.
  ///
  /// In en, this message translates to:
  /// **'Before you can mark this complete:'**
  String get crew_before_complete;

  /// No description provided for @crew_waiting_to_send.
  ///
  /// In en, this message translates to:
  /// **'Waiting to send'**
  String get crew_waiting_to_send;

  /// No description provided for @crew_video.
  ///
  /// In en, this message translates to:
  /// **'Video'**
  String get crew_video;

  /// No description provided for @crew_photo.
  ///
  /// In en, this message translates to:
  /// **'Photo'**
  String get crew_photo;

  /// No description provided for @crew_send_failed.
  ///
  /// In en, this message translates to:
  /// **'Could not send'**
  String get crew_send_failed;

  /// No description provided for @crew_retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get crew_retry;

  /// No description provided for @crew_reason.
  ///
  /// In en, this message translates to:
  /// **'Reason'**
  String get crew_reason;

  /// No description provided for @crew_note_optional.
  ///
  /// In en, this message translates to:
  /// **'Note (optional)'**
  String get crew_note_optional;

  /// No description provided for @crew_add_photo.
  ///
  /// In en, this message translates to:
  /// **'Add a photo (optional)'**
  String get crew_add_photo;

  /// No description provided for @crew_photo_attached.
  ///
  /// In en, this message translates to:
  /// **'Photo attached'**
  String get crew_photo_attached;

  /// No description provided for @crew_confirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get crew_confirm;

  /// No description provided for @crew_marked_could_not_complete.
  ///
  /// In en, this message translates to:
  /// **'Marked as could not complete.'**
  String get crew_marked_could_not_complete;

  /// No description provided for @crew_unassigned.
  ///
  /// In en, this message translates to:
  /// **'Not assigned'**
  String get crew_unassigned;

  /// No description provided for @crew_skip_job.
  ///
  /// In en, this message translates to:
  /// **'Skip job'**
  String get crew_skip_job;

  /// No description provided for @crew_skip_job_body.
  ///
  /// In en, this message translates to:
  /// **'The job is skipped by operations. This cannot be undone here.'**
  String get crew_skip_job_body;

  /// No description provided for @crew_cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get crew_cancel;

  /// No description provided for @crew_job_skipped.
  ///
  /// In en, this message translates to:
  /// **'Job skipped.'**
  String get crew_job_skipped;

  /// No description provided for @crew_reassign.
  ///
  /// In en, this message translates to:
  /// **'Reassign'**
  String get crew_reassign;

  /// No description provided for @crew_reassign_to.
  ///
  /// In en, this message translates to:
  /// **'Reassign to'**
  String get crew_reassign_to;

  /// No description provided for @crew_job_reassigned.
  ///
  /// In en, this message translates to:
  /// **'Job reassigned.'**
  String get crew_job_reassigned;

  /// No description provided for @crew_photo_saved.
  ///
  /// In en, this message translates to:
  /// **'Photo saved'**
  String get crew_photo_saved;

  /// No description provided for @crew_no_photo.
  ///
  /// In en, this message translates to:
  /// **'No photo yet'**
  String get crew_no_photo;

  /// No description provided for @crew_name.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get crew_name;

  /// No description provided for @crew_mobile.
  ///
  /// In en, this message translates to:
  /// **'Mobile number'**
  String get crew_mobile;

  /// No description provided for @crew_role.
  ///
  /// In en, this message translates to:
  /// **'Role'**
  String get crew_role;

  /// No description provided for @crew_working_hours.
  ///
  /// In en, this message translates to:
  /// **'Working hours'**
  String get crew_working_hours;

  /// No description provided for @crew_finish_by.
  ///
  /// In en, this message translates to:
  /// **'Finish by {time}'**
  String crew_finish_by(String time);

  /// No description provided for @crew_finished_at.
  ///
  /// In en, this message translates to:
  /// **'Finished on {date}'**
  String crew_finished_at(String date);

  /// No description provided for @crew_uploads_waiting.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 upload waiting to send} other{{count} uploads waiting to send}}'**
  String crew_uploads_waiting(int count);

  /// No description provided for @crew_uploads_failed.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 upload could not be sent} other{{count} uploads could not be sent}}'**
  String crew_uploads_failed(int count);

  /// No description provided for @crew_photos_progress.
  ///
  /// In en, this message translates to:
  /// **'Photos: {have} of {need} uploaded'**
  String crew_photos_progress(int have, int need);

  /// No description provided for @crew_videos_progress.
  ///
  /// In en, this message translates to:
  /// **'Videos: {have} of {need} uploaded'**
  String crew_videos_progress(int have, int need);

  /// No description provided for @crew_jobs_count.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 job} other{{count} jobs}}'**
  String crew_jobs_count(int count);

  /// No description provided for @crew_stage_before.
  ///
  /// In en, this message translates to:
  /// **'Before'**
  String get crew_stage_before;

  /// No description provided for @crew_stage_during.
  ///
  /// In en, this message translates to:
  /// **'During'**
  String get crew_stage_during;

  /// No description provided for @crew_stage_after.
  ///
  /// In en, this message translates to:
  /// **'After'**
  String get crew_stage_after;

  /// No description provided for @crew_reason_car_not_in_spot.
  ///
  /// In en, this message translates to:
  /// **'Car not in the parking spot'**
  String get crew_reason_car_not_in_spot;

  /// No description provided for @crew_reason_car_locked.
  ///
  /// In en, this message translates to:
  /// **'Car is locked'**
  String get crew_reason_car_locked;

  /// No description provided for @crew_reason_customer_did_not_allow.
  ///
  /// In en, this message translates to:
  /// **'Customer did not allow'**
  String get crew_reason_customer_did_not_allow;

  /// No description provided for @crew_reason_bad_weather.
  ///
  /// In en, this message translates to:
  /// **'Bad weather'**
  String get crew_reason_bad_weather;

  /// No description provided for @crew_reason_other.
  ///
  /// In en, this message translates to:
  /// **'Other'**
  String get crew_reason_other;

  /// No description provided for @money_skipTitle.
  ///
  /// In en, this message translates to:
  /// **'Skip or pause'**
  String get money_skipTitle;

  /// No description provided for @money_skipTab.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get money_skipTab;

  /// No description provided for @money_pauseTab.
  ///
  /// In en, this message translates to:
  /// **'Pause'**
  String get money_pauseTab;

  /// No description provided for @money_skipInstruction.
  ///
  /// In en, this message translates to:
  /// **'Skip must be done by 9 PM the evening before. Requests after the cutoff are not accepted.'**
  String get money_skipInstruction;

  /// No description provided for @money_skipConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm skip'**
  String get money_skipConfirm;

  /// No description provided for @money_skipPickFirst.
  ///
  /// In en, this message translates to:
  /// **'Pick a date to skip first.'**
  String get money_skipPickFirst;

  /// No description provided for @money_skipped.
  ///
  /// In en, this message translates to:
  /// **'Skipped'**
  String get money_skipped;

  /// No description provided for @money_paused.
  ///
  /// In en, this message translates to:
  /// **'Paused'**
  String get money_paused;

  /// No description provided for @money_undoSkip.
  ///
  /// In en, this message translates to:
  /// **'Undo skip'**
  String get money_undoSkip;

  /// No description provided for @money_upcoming.
  ///
  /// In en, this message translates to:
  /// **'Upcoming schedule'**
  String get money_upcoming;

  /// No description provided for @money_pauseFrom.
  ///
  /// In en, this message translates to:
  /// **'From'**
  String get money_pauseFrom;

  /// No description provided for @money_pauseTo.
  ///
  /// In en, this message translates to:
  /// **'To'**
  String get money_pauseTo;

  /// No description provided for @money_pauseChoose.
  ///
  /// In en, this message translates to:
  /// **'Choose the start and end dates first.'**
  String get money_pauseChoose;

  /// No description provided for @money_pauseConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm pause'**
  String get money_pauseConfirm;

  /// No description provided for @money_endPause.
  ///
  /// In en, this message translates to:
  /// **'End pause'**
  String get money_endPause;

  /// No description provided for @money_yourPauses.
  ///
  /// In en, this message translates to:
  /// **'Your pauses'**
  String get money_yourPauses;

  /// No description provided for @money_pauseEnded.
  ///
  /// In en, this message translates to:
  /// **'The pause has ended. Visits resume.'**
  String get money_pauseEnded;

  /// No description provided for @money_callSupport.
  ///
  /// In en, this message translates to:
  /// **'Call support'**
  String get money_callSupport;

  /// No description provided for @money_cutoffClosed.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get money_cutoffClosed;

  /// No description provided for @money_subTitle.
  ///
  /// In en, this message translates to:
  /// **'My subscription'**
  String get money_subTitle;

  /// No description provided for @money_cycle.
  ///
  /// In en, this message translates to:
  /// **'Billing cycle'**
  String get money_cycle;

  /// No description provided for @money_monthly.
  ///
  /// In en, this message translates to:
  /// **'Monthly amount'**
  String get money_monthly;

  /// No description provided for @money_paymentMethod.
  ///
  /// In en, this message translates to:
  /// **'Payment method'**
  String get money_paymentMethod;

  /// No description provided for @money_upi.
  ///
  /// In en, this message translates to:
  /// **'UPI'**
  String get money_upi;

  /// No description provided for @money_latestPayment.
  ///
  /// In en, this message translates to:
  /// **'Latest payment'**
  String get money_latestPayment;

  /// No description provided for @money_payNext.
  ///
  /// In en, this message translates to:
  /// **'Pay for next month'**
  String get money_payNext;

  /// No description provided for @money_pauseService.
  ///
  /// In en, this message translates to:
  /// **'Pause service'**
  String get money_pauseService;

  /// No description provided for @money_billingHistory.
  ///
  /// In en, this message translates to:
  /// **'View billing history'**
  String get money_billingHistory;

  /// No description provided for @money_addons.
  ///
  /// In en, this message translates to:
  /// **'Add-ons'**
  String get money_addons;

  /// No description provided for @money_plan.
  ///
  /// In en, this message translates to:
  /// **'Plan'**
  String get money_plan;

  /// No description provided for @money_cutoff.
  ///
  /// In en, this message translates to:
  /// **'Service cutoff time'**
  String get money_cutoff;

  /// No description provided for @money_interiorDay.
  ///
  /// In en, this message translates to:
  /// **'Interior care day'**
  String get money_interiorDay;

  /// No description provided for @money_noPlanName.
  ///
  /// In en, this message translates to:
  /// **'Plan'**
  String get money_noPlanName;

  /// No description provided for @money_statusOverdue.
  ///
  /// In en, this message translates to:
  /// **'Over due'**
  String get money_statusOverdue;

  /// No description provided for @money_statusInitiated.
  ///
  /// In en, this message translates to:
  /// **'Initiated'**
  String get money_statusInitiated;

  /// No description provided for @money_statusReceived.
  ///
  /// In en, this message translates to:
  /// **'Received'**
  String get money_statusReceived;

  /// No description provided for @money_payTitle.
  ///
  /// In en, this message translates to:
  /// **'Pay by UPI'**
  String get money_payTitle;

  /// No description provided for @money_payAmount.
  ///
  /// In en, this message translates to:
  /// **'Amount to pay'**
  String get money_payAmount;

  /// No description provided for @money_qrMissing.
  ///
  /// In en, this message translates to:
  /// **'The UPI QR code will be shown here.'**
  String get money_qrMissing;

  /// No description provided for @money_payHow.
  ///
  /// In en, this message translates to:
  /// **'Scan the QR code or pay to the UPI ID from any UPI app.'**
  String get money_payHow;

  /// No description provided for @money_upiId.
  ///
  /// In en, this message translates to:
  /// **'UPI ID'**
  String get money_upiId;

  /// No description provided for @money_copy.
  ///
  /// In en, this message translates to:
  /// **'Copy UPI ID'**
  String get money_copy;

  /// No description provided for @money_copied.
  ///
  /// In en, this message translates to:
  /// **'UPI ID copied'**
  String get money_copied;

  /// No description provided for @money_ivePaid.
  ///
  /// In en, this message translates to:
  /// **'I\'ve paid'**
  String get money_ivePaid;

  /// No description provided for @money_submittedTitle.
  ///
  /// In en, this message translates to:
  /// **'Payment submitted'**
  String get money_submittedTitle;

  /// No description provided for @money_goHome.
  ///
  /// In en, this message translates to:
  /// **'Go to home'**
  String get money_goHome;

  /// No description provided for @money_historyTitle.
  ///
  /// In en, this message translates to:
  /// **'Billing history'**
  String get money_historyTitle;

  /// No description provided for @money_historyEmpty.
  ///
  /// In en, this message translates to:
  /// **'No payments yet.'**
  String get money_historyEmpty;

  /// No description provided for @money_invoice.
  ///
  /// In en, this message translates to:
  /// **'Invoice'**
  String get money_invoice;

  /// No description provided for @money_invoiceTitle.
  ///
  /// In en, this message translates to:
  /// **'GST invoice'**
  String get money_invoiceTitle;

  /// No description provided for @money_gstIncluded.
  ///
  /// In en, this message translates to:
  /// **'Price includes GST.'**
  String get money_gstIncluded;

  /// No description provided for @money_addonTitle.
  ///
  /// In en, this message translates to:
  /// **'Deep Spa'**
  String get money_addonTitle;

  /// No description provided for @money_addonDate.
  ///
  /// In en, this message translates to:
  /// **'Preferred date'**
  String get money_addonDate;

  /// No description provided for @money_addonFinishBy.
  ///
  /// In en, this message translates to:
  /// **'Finish by'**
  String get money_addonFinishBy;

  /// No description provided for @money_addonPickDate.
  ///
  /// In en, this message translates to:
  /// **'Choose a date'**
  String get money_addonPickDate;

  /// No description provided for @money_addonConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm & pay'**
  String get money_addonConfirm;

  /// No description provided for @money_addonRequests.
  ///
  /// In en, this message translates to:
  /// **'Your requests'**
  String get money_addonRequests;

  /// No description provided for @money_addonNone.
  ///
  /// In en, this message translates to:
  /// **'No requests yet.'**
  String get money_addonNone;

  /// No description provided for @money_addonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel request'**
  String get money_addonCancel;

  /// No description provided for @money_addonCancelled.
  ///
  /// In en, this message translates to:
  /// **'The request is cancelled. You are not charged.'**
  String get money_addonCancelled;

  /// No description provided for @money_standaloneTitle.
  ///
  /// In en, this message translates to:
  /// **'Deep Spa without a subscription'**
  String get money_standaloneTitle;

  /// No description provided for @money_standaloneBody.
  ///
  /// In en, this message translates to:
  /// **'Tell us when you would like it. Priveo will call you to agree the date, price and payment.'**
  String get money_standaloneBody;

  /// No description provided for @money_contactMobile.
  ///
  /// In en, this message translates to:
  /// **'Mobile number to call'**
  String get money_contactMobile;

  /// No description provided for @money_notes.
  ///
  /// In en, this message translates to:
  /// **'Notes (optional)'**
  String get money_notes;

  /// No description provided for @money_sendRequest.
  ///
  /// In en, this message translates to:
  /// **'Send request'**
  String get money_sendRequest;

  /// No description provided for @money_standaloneDone.
  ///
  /// In en, this message translates to:
  /// **'Request sent. Priveo will call you.'**
  String get money_standaloneDone;

  /// No description provided for @money_standaloneLink.
  ///
  /// In en, this message translates to:
  /// **'Deep Spa without a subscription'**
  String get money_standaloneLink;

  /// No description provided for @money_adminPaymentsTitle.
  ///
  /// In en, this message translates to:
  /// **'Payments to confirm'**
  String get money_adminPaymentsTitle;

  /// No description provided for @money_adminNoPayments.
  ///
  /// In en, this message translates to:
  /// **'Nothing to confirm.'**
  String get money_adminNoPayments;

  /// No description provided for @money_adminConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get money_adminConfirm;

  /// No description provided for @money_adminReject.
  ///
  /// In en, this message translates to:
  /// **'Reject'**
  String get money_adminReject;

  /// No description provided for @money_adminConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Payment confirmed.'**
  String get money_adminConfirmed;

  /// No description provided for @money_adminRejected.
  ///
  /// In en, this message translates to:
  /// **'Payment sent back.'**
  String get money_adminRejected;

  /// No description provided for @money_adminAlertsTitle.
  ///
  /// In en, this message translates to:
  /// **'Alerts'**
  String get money_adminAlertsTitle;

  /// No description provided for @money_adminNoAlerts.
  ///
  /// In en, this message translates to:
  /// **'No alerts.'**
  String get money_adminNoAlerts;

  /// No description provided for @money_adminMarkRead.
  ///
  /// In en, this message translates to:
  /// **'Mark read'**
  String get money_adminMarkRead;

  /// No description provided for @money_skipNote.
  ///
  /// In en, this message translates to:
  /// **'No cleaning on {date}. Your plan isn\'t charged for this visit.'**
  String money_skipNote(String date);

  /// No description provided for @money_skipDone.
  ///
  /// In en, this message translates to:
  /// **'Skipped {date}. The crew has been told.'**
  String money_skipDone(String date);

  /// No description provided for @money_unskipDone.
  ///
  /// In en, this message translates to:
  /// **'{date} is back on. The crew has been told.'**
  String money_unskipDone(String date);

  /// No description provided for @money_pauseDone.
  ///
  /// In en, this message translates to:
  /// **'Paused {from} to {to}. Plan now renews {renewal}.'**
  String money_pauseDone(String from, String to, String renewal);

  /// No description provided for @money_pausePeriod.
  ///
  /// In en, this message translates to:
  /// **'{from} to {to}'**
  String money_pausePeriod(String from, String to);

  /// No description provided for @money_statusDue.
  ///
  /// In en, this message translates to:
  /// **'Due by {date}'**
  String money_statusDue(String date);

  /// No description provided for @money_submittedBody.
  ///
  /// In en, this message translates to:
  /// **'Priveo will confirm your payment of {amount}. Status: Initiated.'**
  String money_submittedBody(String amount);

  /// No description provided for @money_addonSummary.
  ///
  /// In en, this message translates to:
  /// **'{date}, finish by {time}. Total {total}, GST included.'**
  String money_addonSummary(String date, String time, String total);

  /// No description provided for @money_daysLeft.
  ///
  /// In en, this message translates to:
  /// **'{n} days left'**
  String money_daysLeft(int n);

  /// No description provided for @money_addonDuration.
  ///
  /// In en, this message translates to:
  /// **'{minutes} minutes'**
  String money_addonDuration(int minutes);
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
