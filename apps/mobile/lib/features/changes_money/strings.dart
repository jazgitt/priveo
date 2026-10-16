/// The words of the changes and money screens. They mirror
/// `lib/l10n/fragments/money.arb` key for key (the keys there carry the
/// `money_` prefix). When that fragment is merged into `app_en.arb`, these
/// become `AppLocalizations` getters and this file is removed.
library;

class MoneyStrings {
  const MoneyStrings._();

  // Skip and pause (SKIP-, PAUSE-)
  static const skipTitle = 'Skip or pause';
  static const skipTab = 'Skip';
  static const pauseTab = 'Pause';
  static const skipConfirm = 'Confirm skip';
  static const skipPickFirst = 'Pick a date to skip first.';
  static const skipped = 'Skipped';
  static const completed = 'Completed';
  static const paused = 'Paused';
  static const undoSkip = 'Undo skip';
  static String skipDone(String date) => 'Skipped $date. The crew has been told.';
  static String unskipDone(String date) =>
      '$date is back on. The crew has been told.';
  static const pauseFrom = 'From';
  static const pauseTo = 'To';
  static const pauseChoose = 'Choose the start and end dates first.';
  static const pauseConfirm = 'Confirm pause';
  static String pauseDone(String from, String to, String renewal) =>
      'Paused $from to $to. Plan now renews $renewal.';
  static String pausePeriod(String from, String to) => '$from to $to';
  static const endPause = 'End pause';
  static const yourPauses = 'Your pauses';
  static const pauseEnded = 'The pause has ended. Visits resume.';
  static const callSupport = 'Call support';
  static const cutoffClosed = 'Closed';

  // My subscription (SUB-)
  static const subTitle = 'My subscription';
  static String daysLeft(int n) => n == 1 ? '1 day left' : '$n days left';
  static const cycle = 'Billing cycle';
  static const expiresOn = 'Expires on';
  static const monthly = 'Monthly amount';
  static const paymentMethod = 'Payment method';
  static const upi = 'UPI';
  static const latestPayment = 'Latest payment';
  static const payNext = 'Renew subscription';
  static const pauseService = 'Pause service';
  static const billingHistory = 'View billing history';
  static const addons = 'Add-ons';
  static const plan = 'Plan';
  static const cutoff = 'Service cutoff time';
  static const interiorDay = 'Interior care day';
  static const noPlanName = 'Plan';

  // Payment statuses (PAY-09)
  static String statusDue(String date) => 'Due by $date';
  static const statusOverdue = 'Over due';
  static const statusInitiated = 'Initiated';
  static const statusReceived = 'Received';

  // Pay by UPI (PAY-05 to PAY-07)
  static const payTitle = 'Pay by UPI';
  static const renewTitle = 'Renew subscription';
  static const payMethod = 'Payment method';
  static const methodUpi = 'UPI';
  static const methodCard = 'Credit card';
  static const methodCardSoon = 'Coming soon';
  static const payStepsTitle = 'How to pay';
  static const payStepCopy = 'Copy the UPI ID shown below.';
  static String payStepPay(String amount) =>
      'Open any UPI app and pay $amount to this UPI ID.';
  static const payStepConfirm =
      "After you pay, tap \"I've paid\" to submit your confirmation. Priveo will confirm your payment.";
  static const orScan = 'Or scan this QR code from any UPI app.';
  static const payAmount = 'Amount to pay';
  static const qrMissing = 'The UPI QR code will be shown here.';
  static const upiId = 'UPI ID';
  static const copy = 'Copy UPI ID';
  static const copied = 'UPI ID copied';
  static const ivePaid = "I've paid";
  static const submittedTitle = 'Payment submitted';
  static String submittedBody(String amount) =>
      'Priveo will confirm your payment of $amount. Status: Initiated.';
  static const goHome = 'Go to home';

  // Billing history (SUB-06, SUB-12)
  static const historyTitle = 'Billing history';
  static const historyEmpty = 'No payments yet.';
  static const invoice = 'Invoice';
  static const invoiceTitle = 'GST invoice';
  static const gstIncluded = 'Price includes GST.';
  static const invoiceCopy = 'Copy invoice';
  static const invoiceCopied = 'Invoice copied.';
  static const invoiceEmail = 'Email invoice';
  static const invoiceNoMail = 'No email app was found on this phone.';

  // Deep Spa (ADD-)
  static const addonTitle = 'Deep Spa';
  static const addonDate = 'Preferred date';
  static const addonFinishBy = 'Finish by';
  static const addonPickDate = 'Choose a date';
  static const addonConfirm = 'Confirm & pay';
  static const addonRequests = 'Your requests';
  static const addonNone = 'No requests yet.';
  static const addonCancel = 'Cancel request';
  static const addonCancelled = 'The request is cancelled. You are not charged.';
  static String addonSummary(String date, String time, String total) =>
      '$date, finish by $time. Total $total, GST included.';
  static String addonDuration(int minutes) =>
      minutes % 60 == 0 ? '${minutes ~/ 60} hours' : '$minutes minutes';
  static const standaloneTitle = 'Deep Spa without a subscription';
  static const standaloneBody =
      'Choose a date and finish-by time, then pay by UPI. Priveo schedules your service independently of payment.';
  static const contactMobile = 'Mobile number to call';
  static const notes = 'Notes (optional)';
  static const sendRequest = 'Send request';
  static const standaloneDone = 'Booking created. View payment, service status and proof in Deep Spa.';
  static const standaloneLink = 'Deep Spa without a subscription';

  // Admin quick actions (ADM-ACC-07)
  static const adminPaymentsTitle = 'Payments to confirm';
  static const adminNoPayments = 'Nothing to confirm.';
  static const adminConfirm = 'Confirm';
  static const adminReject = 'Reject';
  static const adminConfirmed = 'Payment confirmed.';
  static const adminRejected = 'Payment sent back.';
  static const adminAlertsTitle = 'Alerts';
  static const adminNoAlerts = 'No alerts.';
  static const adminMarkRead = 'Mark read';
}
