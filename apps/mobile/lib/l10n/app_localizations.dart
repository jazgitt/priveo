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
