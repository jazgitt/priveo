/// The words on the crew screens. They mirror `lib/l10n/fragments/crew.arb`
/// (keys `crew_*`), which is merged into `app_en.arb`. They live here until
/// that merge, so these screens do not wait for the generated localizations.
abstract final class CrewText {
  static const offline =
      'Could not reach Priveo. Check the connection and try again.';
  static const team = 'Team';
  static const profile = 'My profile';
  static const allJobs = 'All jobs';
  static const all = 'All';
  static const previousDay = 'Previous day';
  static const nextDay = 'Next day';
  static const noJobs = 'No jobs for this day.';
  static const jobTitle = 'Job';
  static const startJob = 'Start job';
  static const continueJob = 'Continue';
  static const couldNotComplete = 'Could not complete';
  static const service = 'Service';
  static const car = 'Car';
  static const category = 'Category';
  static const society = 'Society';
  static const parking = 'Parking';
  static const finishByLabel = 'Finish by';
  static const slot = 'Slot';
  static const date = 'Date';
  static const checklist = 'Checklist';
  static const assignedTo = 'Assigned to';
  static const skippedByManager = 'Skipped by a Manager';
  static const performTitle = 'Perform service';
  static const proof = 'Photos and video';
  static const takePhoto = 'Take photo';
  static const choosePhoto = 'Choose photo';
  static const recordVideo = 'Record video';
  static const chooseVideo = 'Choose video';
  static const formatNotAccepted = 'This file format is not accepted.';
  static const photoTooLarge = 'A photo must be under 10 MB.';
  static const videoTooLarge = 'A video must be under 25 MB.';
  static const addedToQueue = 'Saved. It will upload when there is a connection.';
  static const captureFailed = 'Could not get the file. Please try again.';
  static const jobCompleted = 'Job completed.';
  static const markComplete = 'Mark complete';
  static const beforeComplete = 'Before you can mark this complete:';
  static const waitingToSend = 'Waiting to send';
  static const video = 'Video';
  static const photo = 'Photo';
  static const sendFailed = 'Could not send';
  static const retry = 'Retry';
  static const remove = 'Remove';
  static const removeUploadTitle = 'Remove this file?';
  static const removeUploadBody =
      'It will not be sent. You can take the photo or video again.';
  static const reason = 'Reason';
  static const noteOptional = 'Note (optional)';
  static const addPhoto = 'Add a photo (optional)';
  static const photoAttached = 'Photo attached';
  static const confirm = 'Confirm';
  static const markedCouldNotComplete = 'Marked as could not complete.';
  static const unassigned = 'Not assigned';
  static const skipJob = 'Skip job';
  static const skipJobBody =
      'The job is skipped by operations. This cannot be undone here.';
  static const cancel = 'Cancel';
  static const jobSkipped = 'Job skipped.';
  static const reassign = 'Reassign';
  static const reassignTo = 'Reassign to';
  static const jobReassigned = 'Job reassigned.';

  // Manager attendance and working hours (CRW-MGR-04, CRW-MGR-05). They
  // mirror `lib/l10n/fragments/crew_manager.arb` (keys `crew_mgr_*`).
  static const attendance = 'Attendance';
  static const workingHours = 'Working hours';
  static const attendancePresent = 'Present';
  static const attendanceSick = 'Sick';
  static const attendanceLeave = 'Leave';
  static const attendanceLateStart = 'Late start';
  static const dayOff = 'Day off';
  static const working = 'Working';
  static const startTime = 'Start';
  static const endTime = 'End';
  static const save = 'Save';
  static const hoursSaved = 'Working hours saved.';
  static const attendanceSaved = 'Attendance saved.';
  static const lateStartFrom = 'Starts at';
  static const chooseLateStart = 'Choose the start time';
  static const noCrew = 'No crew members.';
  static const cannotReassign = 'Cannot take this job';
  static String openJobsCount(int n) => n == 1 ? '1 open job' : '$n open jobs';
  static String lateStartAt(String time) => 'Late start, from $time';
  static String releasedJobs(int moved, int waiting) {
    final parts = <String>[
      if (moved > 0)
        moved == 1 ? '1 job moved to someone else' : '$moved jobs moved to someone else',
      if (waiting > 0)
        waiting == 1
            ? '1 job needs scheduling'
            : '$waiting jobs need scheduling',
    ];
    return '${parts.join('. ')}.';
  }
  static const photoSaved = 'Photo saved';
  static const noPhoto = 'No photo yet';
  static const name = 'Name';
  static const mobile = 'Mobile number';
  static const role = 'Role';

  static String finishBy(String time) => 'Finish by $time';
  static String finishedAt(String date) => 'Finished on $date';
  static String uploadsWaiting(int n) =>
      n == 1 ? '1 upload waiting to send' : '$n uploads waiting to send';
  static String uploadsFailed(int n) =>
      n == 1 ? '1 upload could not be sent' : '$n uploads could not be sent';
  static String photosProgress(int have, int need) =>
      'Photos: $have of $need uploaded';
  static String videosProgress(int have, int need) =>
      'Videos: $have of $need uploaded';
  static String jobsCount(int n) => n == 1 ? '1 job' : '$n jobs';

  static String stage(String stage) => switch (stage) {
        'Before' => 'Before',
        'During' => 'During',
        'After' => 'After',
        _ => stage,
      };

  /// The starting reasons of the API (CRW-CNC-03). An unknown key is shown
  /// as it is.
  static String reasonLabel(String key) => switch (key) {
        'car_not_in_spot' => 'Car not in the parking spot',
        'car_locked' => 'Car is locked',
        'customer_did_not_allow' => 'Customer did not allow',
        'bad_weather' => 'Bad weather',
        'other' => 'Other',
        _ => key,
      };
}
