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

  @override
  String get crew_offline =>
      'Could not reach Priveo. Check the connection and try again.';

  @override
  String get crew_team => 'Team';

  @override
  String get crew_profile => 'My profile';

  @override
  String get crew_all_jobs => 'All jobs';

  @override
  String get crew_all => 'All';

  @override
  String get crew_previous_day => 'Previous day';

  @override
  String get crew_next_day => 'Next day';

  @override
  String get crew_no_jobs => 'No jobs for this day.';

  @override
  String get crew_job_title => 'Job';

  @override
  String get crew_start_job => 'Start job';

  @override
  String get crew_continue_job => 'Continue';

  @override
  String get crew_could_not_complete => 'Could not complete';

  @override
  String get crew_service => 'Service';

  @override
  String get crew_car => 'Car';

  @override
  String get crew_category => 'Category';

  @override
  String get crew_society => 'Society';

  @override
  String get crew_parking => 'Parking';

  @override
  String get crew_finish_by_label => 'Finish by';

  @override
  String get crew_slot => 'Slot';

  @override
  String get crew_date => 'Date';

  @override
  String get crew_checklist => 'Checklist';

  @override
  String get crew_assigned_to => 'Assigned to';

  @override
  String get crew_skipped_by_manager => 'Skipped by a Manager';

  @override
  String get crew_perform_title => 'Perform service';

  @override
  String get crew_proof => 'Photos and video';

  @override
  String get crew_take_photo => 'Take photo';

  @override
  String get crew_choose_photo => 'Choose photo';

  @override
  String get crew_record_video => 'Record video';

  @override
  String get crew_choose_video => 'Choose video';

  @override
  String get crew_format_not_accepted => 'This file format is not accepted.';

  @override
  String get crew_photo_too_large => 'A photo must be under 10 MB.';

  @override
  String get crew_video_too_large => 'A video must be under 25 MB.';

  @override
  String get crew_added_to_queue =>
      'Saved. It will upload when there is a connection.';

  @override
  String get crew_capture_failed => 'Could not get the file. Please try again.';

  @override
  String get crew_job_completed => 'Job completed.';

  @override
  String get crew_mark_complete => 'Mark complete';

  @override
  String get crew_before_complete => 'Before you can mark this complete:';

  @override
  String get crew_waiting_to_send => 'Waiting to send';

  @override
  String get crew_video => 'Video';

  @override
  String get crew_photo => 'Photo';

  @override
  String get crew_send_failed => 'Could not send';

  @override
  String get crew_retry => 'Retry';

  @override
  String get crew_reason => 'Reason';

  @override
  String get crew_note_optional => 'Note (optional)';

  @override
  String get crew_add_photo => 'Add a photo (optional)';

  @override
  String get crew_photo_attached => 'Photo attached';

  @override
  String get crew_confirm => 'Confirm';

  @override
  String get crew_marked_could_not_complete => 'Marked as could not complete.';

  @override
  String get crew_unassigned => 'Not assigned';

  @override
  String get crew_skip_job => 'Skip job';

  @override
  String get crew_skip_job_body =>
      'The job is skipped by operations. This cannot be undone here.';

  @override
  String get crew_cancel => 'Cancel';

  @override
  String get crew_job_skipped => 'Job skipped.';

  @override
  String get crew_reassign => 'Reassign';

  @override
  String get crew_reassign_to => 'Reassign to';

  @override
  String get crew_job_reassigned => 'Job reassigned.';

  @override
  String get crew_photo_saved => 'Photo saved';

  @override
  String get crew_no_photo => 'No photo yet';

  @override
  String get crew_name => 'Name';

  @override
  String get crew_mobile => 'Mobile number';

  @override
  String get crew_role => 'Role';

  @override
  String get crew_working_hours => 'Working hours';

  @override
  String crew_finish_by(String time) {
    return 'Finish by $time';
  }

  @override
  String crew_finished_at(String date) {
    return 'Finished on $date';
  }

  @override
  String crew_uploads_waiting(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count uploads waiting to send',
      one: '1 upload waiting to send',
    );
    return '$_temp0';
  }

  @override
  String crew_uploads_failed(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count uploads could not be sent',
      one: '1 upload could not be sent',
    );
    return '$_temp0';
  }

  @override
  String crew_photos_progress(int have, int need) {
    return 'Photos: $have of $need uploaded';
  }

  @override
  String crew_videos_progress(int have, int need) {
    return 'Videos: $have of $need uploaded';
  }

  @override
  String crew_jobs_count(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count jobs',
      one: '1 job',
    );
    return '$_temp0';
  }

  @override
  String get crew_stage_before => 'Before';

  @override
  String get crew_stage_during => 'During';

  @override
  String get crew_stage_after => 'After';

  @override
  String get crew_reason_car_not_in_spot => 'Car not in the parking spot';

  @override
  String get crew_reason_car_locked => 'Car is locked';

  @override
  String get crew_reason_customer_did_not_allow => 'Customer did not allow';

  @override
  String get crew_reason_bad_weather => 'Bad weather';

  @override
  String get crew_reason_other => 'Other';

  @override
  String get money_skipTitle => 'Skip or pause';

  @override
  String get money_skipTab => 'Skip';

  @override
  String get money_pauseTab => 'Pause';

  @override
  String get money_skipInstruction =>
      'Skip must be done by 9 PM the evening before. Requests after the cutoff are not accepted.';

  @override
  String get money_skipConfirm => 'Confirm skip';

  @override
  String get money_skipPickFirst => 'Pick a date to skip first.';

  @override
  String get money_skipped => 'Skipped';

  @override
  String get money_paused => 'Paused';

  @override
  String get money_undoSkip => 'Undo skip';

  @override
  String get money_upcoming => 'Upcoming schedule';

  @override
  String get money_pauseFrom => 'From';

  @override
  String get money_pauseTo => 'To';

  @override
  String get money_pauseChoose => 'Choose the start and end dates first.';

  @override
  String get money_pauseConfirm => 'Confirm pause';

  @override
  String get money_endPause => 'End pause';

  @override
  String get money_yourPauses => 'Your pauses';

  @override
  String get money_pauseEnded => 'The pause has ended. Visits resume.';

  @override
  String get money_callSupport => 'Call support';

  @override
  String get money_cutoffClosed => 'Closed';

  @override
  String get money_subTitle => 'My subscription';

  @override
  String get money_cycle => 'Billing cycle';

  @override
  String get money_monthly => 'Monthly amount';

  @override
  String get money_paymentMethod => 'Payment method';

  @override
  String get money_upi => 'UPI';

  @override
  String get money_latestPayment => 'Latest payment';

  @override
  String get money_payNext => 'Pay for next month';

  @override
  String get money_pauseService => 'Pause service';

  @override
  String get money_billingHistory => 'View billing history';

  @override
  String get money_addons => 'Add-ons';

  @override
  String get money_plan => 'Plan';

  @override
  String get money_cutoff => 'Service cutoff time';

  @override
  String get money_interiorDay => 'Interior care day';

  @override
  String get money_noPlanName => 'Plan';

  @override
  String get money_statusOverdue => 'Over due';

  @override
  String get money_statusInitiated => 'Initiated';

  @override
  String get money_statusReceived => 'Received';

  @override
  String get money_payTitle => 'Pay by UPI';

  @override
  String get money_payAmount => 'Amount to pay';

  @override
  String get money_qrMissing => 'The UPI QR code will be shown here.';

  @override
  String get money_payHow =>
      'Scan the QR code or pay to the UPI ID from any UPI app.';

  @override
  String get money_upiId => 'UPI ID';

  @override
  String get money_copy => 'Copy UPI ID';

  @override
  String get money_copied => 'UPI ID copied';

  @override
  String get money_ivePaid => 'I\'ve paid';

  @override
  String get money_submittedTitle => 'Payment submitted';

  @override
  String get money_goHome => 'Go to home';

  @override
  String get money_historyTitle => 'Billing history';

  @override
  String get money_historyEmpty => 'No payments yet.';

  @override
  String get money_invoice => 'Invoice';

  @override
  String get money_invoiceTitle => 'GST invoice';

  @override
  String get money_gstIncluded => 'Price includes GST.';

  @override
  String get money_addonTitle => 'Deep Spa';

  @override
  String get money_addonDate => 'Preferred date';

  @override
  String get money_addonFinishBy => 'Finish by';

  @override
  String get money_addonPickDate => 'Choose a date';

  @override
  String get money_addonConfirm => 'Confirm & pay';

  @override
  String get money_addonRequests => 'Your requests';

  @override
  String get money_addonNone => 'No requests yet.';

  @override
  String get money_addonCancel => 'Cancel request';

  @override
  String get money_addonCancelled =>
      'The request is cancelled. You are not charged.';

  @override
  String get money_standaloneTitle => 'Deep Spa without a subscription';

  @override
  String get money_standaloneBody =>
      'Tell us when you would like it. Priveo will call you to agree the date, price and payment.';

  @override
  String get money_contactMobile => 'Mobile number to call';

  @override
  String get money_notes => 'Notes (optional)';

  @override
  String get money_sendRequest => 'Send request';

  @override
  String get money_standaloneDone => 'Request sent. Priveo will call you.';

  @override
  String get money_standaloneLink => 'Deep Spa without a subscription';

  @override
  String get money_adminPaymentsTitle => 'Payments to confirm';

  @override
  String get money_adminNoPayments => 'Nothing to confirm.';

  @override
  String get money_adminConfirm => 'Confirm';

  @override
  String get money_adminReject => 'Reject';

  @override
  String get money_adminConfirmed => 'Payment confirmed.';

  @override
  String get money_adminRejected => 'Payment sent back.';

  @override
  String get money_adminAlertsTitle => 'Alerts';

  @override
  String get money_adminNoAlerts => 'No alerts.';

  @override
  String get money_adminMarkRead => 'Mark read';

  @override
  String money_skipNote(String date) {
    return 'No cleaning on $date. Your plan isn\'t charged for this visit.';
  }

  @override
  String money_skipDone(String date) {
    return 'Skipped $date. The crew has been told.';
  }

  @override
  String money_unskipDone(String date) {
    return '$date is back on. The crew has been told.';
  }

  @override
  String money_pauseDone(String from, String to, String renewal) {
    return 'Paused $from to $to. Plan now renews $renewal.';
  }

  @override
  String money_pausePeriod(String from, String to) {
    return '$from to $to';
  }

  @override
  String money_statusDue(String date) {
    return 'Due by $date';
  }

  @override
  String money_submittedBody(String amount) {
    return 'Priveo will confirm your payment of $amount. Status: Initiated.';
  }

  @override
  String money_addonSummary(String date, String time, String total) {
    return '$date, finish by $time. Total $total, GST included.';
  }

  @override
  String money_daysLeft(int n) {
    return '$n days left';
  }

  @override
  String money_addonDuration(int minutes) {
    return '$minutes minutes';
  }

  @override
  String get adminq_home_complaints => 'Complaints';

  @override
  String get adminq_home_feedback => 'Feedback and ratings';

  @override
  String get adminq_home_needs_scheduling => 'Needs scheduling';

  @override
  String get adminq_home_day => 'Day schedule';

  @override
  String get adminq_home_capacity => 'Capacity';

  @override
  String get adminq_home_open_complaints => 'Open complaints';

  @override
  String get adminq_home_to_confirm => 'To confirm';

  @override
  String adminq_home_more_payments(String count) {
    return '$count more to confirm';
  }

  @override
  String get adminq_filter_all => 'All';

  @override
  String get adminq_status_raised => 'Raised';

  @override
  String get adminq_status_in_progress => 'In progress';

  @override
  String get adminq_status_resolved => 'Resolved';

  @override
  String get adminq_complaints_title => 'Complaints';

  @override
  String get adminq_complaints_empty => 'No complaints.';

  @override
  String get adminq_complaint_overdue => 'Open for more than 4 hours';

  @override
  String adminq_complaint_raised_on(String date) {
    return 'Raised $date';
  }

  @override
  String get adminq_complaint_status => 'Status';

  @override
  String get adminq_complaint_note_hint => 'Write a note';

  @override
  String get adminq_complaint_note_required => 'Write a note first.';

  @override
  String get adminq_complaint_add_note => 'Add note';

  @override
  String get adminq_complaint_save_status => 'Save status';

  @override
  String get adminq_complaint_saved => 'Saved.';

  @override
  String get adminq_complaint_thread => 'History';

  @override
  String get adminq_complaint_by_customer => 'Customer';

  @override
  String get adminq_complaint_by_admin => 'Priveo';

  @override
  String adminq_complaint_status_changed(String status) {
    return 'Status: $status';
  }

  @override
  String get adminq_feedback_title => 'Feedback and ratings';

  @override
  String get adminq_feedback_empty => 'No feedback yet.';

  @override
  String get adminq_feedback_ratings => 'Visit ratings';

  @override
  String adminq_feedback_average(String average, String count) {
    return 'Average $average from $count ratings';
  }

  @override
  String get adminq_feedback_no_ratings => 'No ratings yet.';

  @override
  String adminq_feedback_stars(String n) {
    return '$n stars';
  }

  @override
  String get adminq_needs_title => 'Needs scheduling';

  @override
  String get adminq_needs_empty => 'Every job has a crew member.';

  @override
  String get adminq_day_title => 'Day schedule';

  @override
  String adminq_day_summary(String total, String done, String left) {
    return '$total jobs, $done done, $left left';
  }

  @override
  String get adminq_day_empty => 'No jobs on this date.';

  @override
  String adminq_day_status(String status) {
    return 'Schedule: $status';
  }

  @override
  String get adminq_day_all_societies => 'All societies';

  @override
  String get adminq_day_previous => 'Previous day';

  @override
  String get adminq_day_next => 'Next day';

  @override
  String get adminq_day_late => 'Late';

  @override
  String get adminq_day_no_time => 'No time';

  @override
  String get adminq_capacity_title => 'Capacity';

  @override
  String get adminq_capacity_empty => 'Choose a society to see its capacity.';

  @override
  String adminq_capacity_line(
    String capacity,
    String demand,
    String scheduled,
  ) {
    return 'Crew $capacity min, work $demand min, placed $scheduled min';
  }

  @override
  String get adminq_capacity_over => 'Over capacity';

  @override
  String get adminq_capacity_previous => 'Previous week';

  @override
  String get adminq_capacity_next => 'Next week';

  @override
  String get adminq_society => 'Society';

  @override
  String get cust_proof_crew_line => 'Priveo crew';

  @override
  String get cust_proof_crew_pending => 'Crew member not assigned yet';

  @override
  String get cust_proof_checklist_heading => 'Checklist';

  @override
  String get cust_proof_after_label => 'AFTER';

  @override
  String get cust_proof_rate_clean => 'Rate this clean';

  @override
  String get cust_proof_change_rating => 'Change rating';

  @override
  String get cust_proof_report_issue => 'Report an issue with this clean';

  @override
  String get cust_proof_load_more => 'Load more';

  @override
  String get cust_proof_no_rating => 'Not rated';

  @override
  String get cust_proof_history_month_empty => 'No services in this month.';

  @override
  String get cust_proof_today_done => 'Today\'s clean is done';

  @override
  String get cust_proof_view_proof => 'View proof';

  @override
  String get cust_proof_rate_today => 'Rate today\'s clean';

  @override
  String get money_invoiceCopy => 'Copy invoice';

  @override
  String get money_invoiceCopied => 'Invoice copied.';

  @override
  String get money_invoiceEmail => 'Email invoice';

  @override
  String get money_invoiceNoMail => 'No email app was found on this phone.';

  @override
  String get support_faq => 'Frequently asked questions';

  @override
  String get support_faq_empty => 'There are no questions yet.';

  @override
  String get support_feedback_tab => 'Feedback';

  @override
  String get auth_welcome_title => 'Welcome to Priveo';

  @override
  String get auth_get_started => 'Get started';

  @override
  String get auth_already_member => 'Already a member? Log in';

  @override
  String get auth_email_invalid => 'Enter a valid email address.';

  @override
  String get auth_terms_prefix => 'By continuing you accept the ';

  @override
  String get auth_terms_link => 'Terms';

  @override
  String get auth_terms_and => ' and the ';

  @override
  String get auth_privacy_link => 'Privacy Policy';

  @override
  String get auth_terms_suffix => '.';

  @override
  String get auth_call_support => 'Call support';

  @override
  String get auth_whatsapp_support => 'WhatsApp support';

  @override
  String get crew_mgr_attendance => 'Attendance';

  @override
  String get crew_mgr_working_hours => 'Working hours';

  @override
  String get crew_mgr_present => 'Present';

  @override
  String get crew_mgr_sick => 'Sick';

  @override
  String get crew_mgr_leave => 'Leave';

  @override
  String get crew_mgr_late_start => 'Late start';

  @override
  String get crew_mgr_day_off => 'Day off';

  @override
  String get crew_mgr_working => 'Working';

  @override
  String get crew_mgr_start_time => 'Start';

  @override
  String get crew_mgr_end_time => 'End';

  @override
  String get crew_mgr_save => 'Save';

  @override
  String get crew_mgr_hours_saved => 'Working hours saved.';

  @override
  String get crew_mgr_attendance_saved => 'Attendance saved.';

  @override
  String get crew_mgr_late_start_from => 'Starts at';

  @override
  String get crew_mgr_choose_late_start => 'Choose the start time';

  @override
  String get crew_mgr_no_crew => 'No crew members.';

  @override
  String get crew_mgr_cannot_reassign => 'Cannot take this job';

  @override
  String crew_mgr_open_jobs_count(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count open jobs',
      one: '1 open job',
    );
    return '$_temp0';
  }

  @override
  String crew_mgr_late_start_at(String time) {
    return 'Late start, from $time';
  }

  @override
  String crew_mgr_released_moved(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count jobs moved to someone else',
      one: '1 job moved to someone else',
    );
    return '$_temp0';
  }

  @override
  String crew_mgr_released_waiting(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count jobs need scheduling',
      one: '1 job needs scheduling',
    );
    return '$_temp0';
  }

  @override
  String get addVehicleTitle => 'Add vehicle';

  @override
  String get addVehicleSociety => 'Society';

  @override
  String get addVehicleCar => 'Vehicle details';

  @override
  String get addVehicleParking => 'Parking';

  @override
  String get addVehiclePlan => 'Plan';

  @override
  String get addVehiclePreferences => 'Service preferences';

  @override
  String get addVehicleReview => 'Review and payment';

  @override
  String get addVehicleSearch => 'Search societies';

  @override
  String get addVehicleNoSocieties =>
      'No serviced societies available at the moment.';

  @override
  String get addVehicleSocietyFixed =>
      'Your vehicle\'s society cannot be changed after it is added.';

  @override
  String get addVehicleMake => 'Make';

  @override
  String get addVehicleModel => 'Model';

  @override
  String get addVehicleVariant => 'Variant';

  @override
  String get addVehicleStandard => 'Standard';

  @override
  String get addVehicleAuto => 'Auto-detected';

  @override
  String get addVehicleRegistration => 'Registration number';

  @override
  String get addVehiclePhoto => 'Add vehicle photo (required)';

  @override
  String get addVehicleReplacePhoto => 'Replace vehicle photo';

  @override
  String get addVehicleRc => 'Upload RC document (optional)';

  @override
  String get addVehicleRcUploaded => 'RC uploaded Â· Replace';

  @override
  String get addVehicleRcLimit =>
      'Choose a JPG, PNG or PDF document up to 5 MB.';

  @override
  String get addVehicleBasement => 'Basement';

  @override
  String get addVehicleParkingNumber => 'Parking number';

  @override
  String get addVehicleCancel => 'Cancel anytime';

  @override
  String get addVehicleCutoff => 'Service cutoff time';

  @override
  String get addVehicleSlotNote =>
      'Choose when your clean should be finished. Priveo assigns the exact slot.';

  @override
  String get addVehicleInterior => 'Interior care day';

  @override
  String get addVehicleTotal => 'Total payable today includes GST.';

  @override
  String get addVehicleStartNote => 'Priveo will confirm the start date.';

  @override
  String get addVehicleBack => 'Back';

  @override
  String get addVehicleConfirm => 'Confirm & pay';

  @override
  String get addVehicleRequired =>
      'Complete the required details before continuing.';

  @override
  String get addonChangeRequest => 'Change requested, awaiting Priveo';

  @override
  String get addonChangeAction => 'Change date or time';

  @override
  String get addonNoOffers => 'No add-ons are available at the moment.';

  @override
  String get addonSupportClosed => 'Changes are closed. Call support for help.';

  @override
  String get addonViewProof => 'View service details';

  @override
  String get adminCustomers => 'Customers';

  @override
  String get adminCustomerSearch =>
      'Search name, mobile, registration or society';

  @override
  String get adminNoCustomers => 'No customers found.';

  @override
  String get adminCustomerDetails => 'Customer details';

  @override
  String get adminEmailVerified => 'Email verified';

  @override
  String get adminYes => 'Yes';

  @override
  String get adminNo => 'No';

  @override
  String get adminFromDate => 'From date';

  @override
  String get adminToDate => 'To date';

  @override
  String get adminSkipDate => 'Skip date';

  @override
  String get adminPause => 'Pause';

  @override
  String get adminRenewal => 'Renewal';

  @override
  String get adminUnskip => 'Un-skip';

  @override
  String get adminEndPause => 'End pause';

  @override
  String get adminOperations => 'Operations';

  @override
  String get adminQueue => 'Queue';

  @override
  String get adminMissedJobs => 'Missed jobs';

  @override
  String get adminScheduledWork => 'Scheduled work';

  @override
  String get adminOutcomeHistory => 'Resolution history';

  @override
  String get adminSocietyFilter => 'Society filter';

  @override
  String get adminAllSocieties => 'All societies';

  @override
  String get adminFailureReason => 'Failure reason';

  @override
  String get adminAllReasons => 'All reasons';

  @override
  String get adminClearDates => 'Clear dates';

  @override
  String get adminNoJobs => 'No jobs match these filters.';

  @override
  String get adminMissed => 'Missed';

  @override
  String get adminUnassigned => 'Unassigned';

  @override
  String get adminCoveredOn =>
      'Covered by the next dayâ€™s regular Exterior service on';

  @override
  String get adminRescheduledOn => 'Rescheduled on';

  @override
  String get adminAssigned => 'Assigned';

  @override
  String get adminNeedsAssignment => 'Needs scheduling';

  @override
  String get adminOperationsReason => 'Operations reason';

  @override
  String get adminOptionalReason => 'No reason selected';

  @override
  String get adminOutcomeNote => 'Outcome note';

  @override
  String get adminExteriorExtension =>
      'Skipping adds one day to the plan and moves unpaid renewal dates.';

  @override
  String get adminSpaSkip =>
      'Skipping does not extend the plan. Handle any refund or rebooking separately.';

  @override
  String get adminInteriorSkip =>
      'Skipping loses this Interior service and does not extend the plan.';

  @override
  String get adminSkipJob => 'Skip job by operations';

  @override
  String get adminRetryNextDay => 'Reschedule for next day';

  @override
  String get adminSkipVisit => 'Skip remaining jobs on this visit';

  @override
  String get adminCrew => 'Crew';

  @override
  String get adminNoCrew => 'No crew found.';

  @override
  String get adminAddException => 'Add crew exception';

  @override
  String get adminExceptionType => 'Exception type';

  @override
  String get adminSick => 'Sick';

  @override
  String get adminLeave => 'Leave';

  @override
  String get adminLateStart => 'Late start';

  @override
  String get adminStartTime => 'Start time';

  @override
  String get adminSave => 'Save';

  @override
  String get adminAddonRequests => 'Add-on requests';

  @override
  String get adminStatusFilter => 'Status filter';

  @override
  String get adminAllStatuses => 'All statuses';

  @override
  String get adminNoAddons => 'No add-on requests.';

  @override
  String get adminStandaloneRequest => 'Standalone request';

  @override
  String get adminChangeRequested => 'Change requested';

  @override
  String get adminCheckins => 'Monthly check-in results';

  @override
  String get adminNoCheckins => 'No check-in results.';

  @override
  String get adminOperationsForDay => 'Operations for this day';

  @override
  String get invoiceOpenPdf => 'Open invoice PDF';

  @override
  String get invoicePdfTitle => 'Invoice PDF';

  @override
  String get invoicePdfUnavailable =>
      'The invoice PDF could not be opened. Please try again.';

  @override
  String get proofVideoTitle => 'Proof video';

  @override
  String get proofVideoUnavailable =>
      'The video could not be played. Check your connection and try again.';

  @override
  String get proofVideoMissing =>
      'This video is no longer available for this visit.';

  @override
  String get proofVideoPlay => 'Play';

  @override
  String get proofVideoPause => 'Pause';

  @override
  String get proofVideoReplay => 'Replay';
}
