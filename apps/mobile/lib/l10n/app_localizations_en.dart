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

  @override
  String get cust_calendar_title => 'Service calendar';

  @override
  String get cust_previous_month => 'Previous month';

  @override
  String get cust_next_month => 'Next month';

  @override
  String get cust_legend_done => 'Completed';

  @override
  String get cust_legend_interior => 'Exterior + Interior';

  @override
  String get cust_legend_spa => 'Deep Spa';

  @override
  String get cust_legend_scheduled => 'Scheduled';

  @override
  String get cust_legend_skipped => 'Skipped';

  @override
  String get cust_legend_missed => 'Missed';

  @override
  String get cust_no_visit => 'No visit on this day.';

  @override
  String get cust_no_visit_chip => 'No visit';

  @override
  String get cust_view_details => 'View service details';

  @override
  String get cust_proof_after_visit => 'Proof appears after the visit.';

  @override
  String get cust_you_skipped => 'You skipped this date.';

  @override
  String get cust_missed_note => 'This service was missed.';

  @override
  String cust_scheduled_by(String time) {
    return 'Scheduled to be completed by $time. Proof appears after the visit.';
  }

  @override
  String get cust_history_title => 'Service history';

  @override
  String get cust_history_empty => 'No services yet.';

  @override
  String cust_photo_count(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count photos',
      one: '1 photo',
    );
    return '$_temp0';
  }

  @override
  String get cust_visit_title => 'Service details';

  @override
  String get cust_jobs_heading => 'Jobs';

  @override
  String get cust_photos_heading => 'Photos';

  @override
  String get cust_videos_heading => 'Videos';

  @override
  String get cust_no_proof_yet =>
      'Photos and videos appear once the service is done.';

  @override
  String get cust_play_video => 'Play video';

  @override
  String get cust_photo_unavailable => 'Photo unavailable';

  @override
  String get cust_close => 'Close';

  @override
  String cust_photo_position(int index, int total) {
    return '$index / $total';
  }

  @override
  String get cust_vehicles_title => 'My vehicles';

  @override
  String get cust_vehicles_empty => 'No vehicles yet.';

  @override
  String get cust_no_subscription => 'No subscription';

  @override
  String get cust_number_to_be_added => 'Number to be added';

  @override
  String get cust_vehicle_title => 'Vehicle';

  @override
  String get cust_field_registration => 'Registration';

  @override
  String get cust_field_car => 'Make and model';

  @override
  String get cust_field_variant => 'Variant';

  @override
  String get cust_field_category => 'Category';

  @override
  String get cust_field_society => 'Society';

  @override
  String get cust_field_parking => 'Parking';

  @override
  String get cust_field_plan => 'Plan';

  @override
  String get cust_field_cutoff => 'Service cutoff time';

  @override
  String get cust_field_interior_day => 'Interior care day';

  @override
  String get cust_not_on_file => 'Not on file';

  @override
  String get cust_car_details_via_support =>
      'Car details change only through Priveo support.';

  @override
  String get cust_account_title => 'My account';

  @override
  String get cust_account_vehicles => 'My vehicles';

  @override
  String get cust_account_history => 'Service history';

  @override
  String get cust_account_notifications => 'Notifications';

  @override
  String get cust_account_sign_out => 'Sign out';

  @override
  String get cust_settings_heading => 'Settings';

  @override
  String get cust_settings_note =>
      'Notification choices will be available in a later update.';

  @override
  String get cust_notifications_title => 'Notifications';

  @override
  String get cust_notifications_empty => 'No notifications yet.';

  @override
  String get cust_mark_all_read => 'Mark all as read';

  @override
  String get cust_next_service_heading => 'Next service';

  @override
  String get people_crewProfileTitle => 'My profile';

  @override
  String get people_role => 'Role';

  @override
  String get people_workingHours => 'Working hours';

  @override
  String get people_dayOff => 'Off';

  @override
  String people_hoursRange(String start, String end) {
    return '$start to $end';
  }

  @override
  String get people_profileNote =>
      'Your name, mobile number, society and role are set by Priveo.';

  @override
  String get people_profileMissing =>
      'Your details are not set up yet. Contact Priveo.';

  @override
  String get people_vehiclesTitle => 'My vehicles';

  @override
  String get people_vehicleDetails => 'Vehicle details';

  @override
  String get people_subscriptionStatus => 'Subscription status';

  @override
  String get people_monthlyAmount => 'Monthly amount';

  @override
  String get people_vehicleNotFound => 'This vehicle is not on your account.';

  @override
  String get support_title => 'Help and support';

  @override
  String get support_call => 'Call support';

  @override
  String get support_whatsapp => 'WhatsApp support';

  @override
  String support_hours(String hours) {
    return 'Support hours: $hours';
  }

  @override
  String get support_report_issue => 'Report an issue';

  @override
  String get support_my_complaints => 'My complaints';

  @override
  String support_complaints_in_progress(String count) {
    return '$count in progress';
  }

  @override
  String get support_give_feedback => 'Give feedback';

  @override
  String get support_monthly_checkin => 'Monthly check-in';

  @override
  String get support_cannot_open => 'We could not open that. Please try again.';

  @override
  String get support_report_title => 'Report an issue';

  @override
  String get support_issue_category => 'What went wrong?';

  @override
  String get support_issue_choose => 'Choose what went wrong.';

  @override
  String get support_issue_linked_visit =>
      'This report is linked to the clean you came from.';

  @override
  String get support_issue_description => 'Describe what happened';

  @override
  String get support_issue_description_required => 'Describe what happened.';

  @override
  String get support_issue_send => 'Send report';

  @override
  String get support_issue_sent => 'Thank you. We will reply within 4 hours.';

  @override
  String get support_complaints_title => 'My complaints';

  @override
  String get support_complaints_empty => 'You have not raised any complaints.';

  @override
  String support_complaint_raised_on(String date) {
    return 'Raised $date';
  }

  @override
  String get support_complaint_reply_hint => 'Write a reply';

  @override
  String get support_complaint_send => 'Send';

  @override
  String get support_complaint_resolved =>
      'This complaint is resolved. Raise a new one if the problem is back.';

  @override
  String get support_thread_you => 'You';

  @override
  String get support_thread_priveo => 'Priveo';

  @override
  String support_status_changed(String status) {
    return 'Status: $status';
  }

  @override
  String get support_feedback_title => 'Give feedback';

  @override
  String get support_feedback_category => 'What is it about? (optional)';

  @override
  String get support_feedback_rating => 'Your rating';

  @override
  String get support_feedback_comment => 'Comments';

  @override
  String get support_feedback_testimonial =>
      'Priveo may quote my feedback as a testimonial.';

  @override
  String get support_feedback_send => 'Send';

  @override
  String get support_feedback_thanks => 'Thank you for your feedback.';

  @override
  String support_star(String n) {
    return 'Rate $n out of 5';
  }

  @override
  String get support_rate_title => 'Rate this clean';

  @override
  String get support_rate_positive_tags => 'What went well? (optional)';

  @override
  String get support_rate_issue_tags => 'What could be better? (optional)';

  @override
  String get support_rate_thanks => 'Thank you for rating this clean.';

  @override
  String get support_checkin_title => 'Monthly check-in';

  @override
  String support_checkin_intro(String vehicle) {
    return 'How is Priveo doing for $vehicle? Tap a star for any of these.';
  }

  @override
  String get support_checkin_comment => 'Anything else? (optional)';

  @override
  String get support_checkin_submit => 'Submit';

  @override
  String get support_checkin_thanks => 'Thank you. Your check-in is saved.';

  @override
  String get support_checkin_none => 'There is no check-in to give right now.';

  @override
  String get support_crew_ratings_title => 'Ratings';

  @override
  String get support_crew_ratings_note =>
      'Customers rate each visit as a whole. A rating is never given to a crew member.';

  @override
  String get support_crew_ratings_average => 'Average rating';

  @override
  String support_crew_ratings_count(String count, String days) {
    return '$count ratings in the last $days days';
  }

  @override
  String get support_crew_ratings_none => 'No ratings yet.';

  @override
  String get support_alerts_title => 'Alerts';

  @override
  String support_alerts_unread(String count) {
    return '$count unread';
  }

  @override
  String get support_alerts_empty => 'No alerts.';

  @override
  String get support_alerts_mark_all => 'Mark all as read';
}
