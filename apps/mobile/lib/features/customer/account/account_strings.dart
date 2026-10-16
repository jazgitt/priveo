/// English text of the account, profile and photo screens (ACC-, VEH-, ISS-).
/// The same keys, prefixed `cust_acct_` and in snake case, are in
/// `lib/l10n/fragments/customer_account.arb`; the coordinator merges them.
class AccountStrings {
  const AccountStrings._();

  static const editProfile = 'Edit profile';
  static const profileSaved = 'Your profile is saved.';
  static const firstName = 'First name';
  static const lastName = 'Last name';
  static const mobile = 'Mobile number';
  static const email = 'Email';
  static const enterFirstName = 'Enter your first name, using letters only.';
  static const enterLastName = 'Enter your last name, using letters only.';
  static const enterMobile = 'Enter a 10-digit mobile number.';
  static const save = 'Save';
  static const changeEmail = 'Change email';
  static const newEmail = 'New email';
  static const enterEmail = 'Enter a valid email.';
  static const sendCode = 'Send code';
  static const emailCodeSent =
      'We sent a 6-digit code to the new email. Your old email stays in use until you enter it.';
  static const code = '6-digit code';
  static const verify = 'Verify email';
  static const emailChanged = 'Your email is changed.';
  static const pendingEmail = 'Waiting for the code sent to';
  static const changePassword = 'Change password';
  static const currentPassword = 'Current password';
  static const newPassword = 'New password';
  static const passwordRule =
      'Use at least 8 characters, with a letter and a number.';
  static const passwordChanged = 'Your password is changed.';
  static const memberSince = 'Member since';
  static const subscriptions = 'Subscriptions';
  static const renews = 'Renews';
  static const expires = 'Expires on';
  static const perMonth = 'a month';
  static const menuCalendar = 'Service calendar';
  static const menuAddons = 'Add-ons';
  static const menuSkipPause = 'Skip or pause service';
  static const menuComplaints = 'My complaints';
  static const menuHelp = 'Help & support';
  static const chooseVehicle = 'Choose a vehicle';

  // Vehicle photo and parking (VEH-01, VEH-03, VEH-04, ONB-22).
  static const vehiclePhoto = 'Vehicle photo';
  static const addPhoto = 'Add a photo of your car';
  static const changePhoto = 'Change photo';
  static const takePhoto = 'Take a photo';
  static const fromGallery = 'Choose from gallery';
  static const photoRequired = 'Add a photo of your car to continue.';
  static const photoFormat = 'This file format is not accepted.';
  static const photoTooLarge = 'A photo must be under 10 MB.';
  static const uploading = 'Sending the photo...';
  static const uploadFailed = 'The photo could not be sent. Please try again.';
  static const retry = 'Try again';
  static const rcDocument = 'RC document';
  static const rcUploaded = 'Uploaded';
  static const rcNotUploaded = 'Not uploaded';
  static const editParking = 'Edit parking';
  static const basement = 'Basement';
  static const parkingNumber = 'Parking number';
  static const parkingSaved = 'Your parking details are saved.';
  static const selectBasement = 'Select the basement.';
  static const enterParking = 'Enter the parking number, in digits.';

  // Report an issue (ISS-02, ISS-04).
  static const linkedVisit = 'Linked visit';
  static const noLinkedVisit = 'No linked visit';
  static const attachPhotos = 'Photos (optional)';
  static const addComplaintPhoto = 'Add a photo';
  static const removePhoto = 'Remove photo';
}
