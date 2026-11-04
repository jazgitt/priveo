/// Hand-written DTOs for the changes and money endpoints. They move into the
/// generated client when the contract is regenerated at integration.
library;

DateTime _date(Object? v) => DateTime.parse(v! as String);
DateTime? _dateOrNull(Object? v) =>
    v == null ? null : DateTime.parse(v as String);

/// A skip, a pause or a cutoff change.
class ChangeDto {
  const ChangeDto({
    required this.id,
    required this.kind,
    required this.status,
    required this.startDate,
    required this.endDate,
    required this.days,
    this.visitsPaused,
    this.renewalDate,
  });

  final String id;
  final String kind;
  final String status;
  final DateTime startDate;
  final DateTime endDate;
  final int days;
  final int? visitsPaused;
  final DateTime? renewalDate;

  factory ChangeDto.fromJson(Map<String, dynamic> j) => ChangeDto(
    id: j['id'] as String,
    kind: j['kind'] as String,
    status: j['status'] as String,
    startDate: _date(j['start_date']),
    endDate: _date(j['end_date']),
    days: j['days'] as int,
    visitsPaused: j['visits_paused'] as int?,
    renewalDate: _dateOrNull(j['renewal_date']),
  );
}

class ChangesDto {
  const ChangesDto({
    required this.skips,
    required this.pauses,
    this.renewalDate,
    this.planEndsOn,
  });

  final List<ChangeDto> skips;
  final List<ChangeDto> pauses;
  final DateTime? renewalDate;

  /// The last day the current plan covers: skip and pause stop here.
  final DateTime? planEndsOn;

  factory ChangesDto.fromJson(Map<String, dynamic> j) => ChangesDto(
    skips: [
      for (final s in j['skips'] as List)
        ChangeDto.fromJson(s as Map<String, dynamic>),
    ],
    pauses: [
      for (final s in j['pauses'] as List)
        ChangeDto.fromJson(s as Map<String, dynamic>),
    ],
    renewalDate: _dateOrNull(j['renewal_date']),
    planEndsOn: _dateOrNull(j['plan_ends_on']),
  );
}

/// One upcoming service day (SKIP-01).
class UpcomingDayDto {
  const UpcomingDayDto({
    required this.date,
    required this.services,
    required this.state,
    required this.canChange,
    this.skipId,
  });

  final DateTime date;
  final List<String> services;

  /// Scheduled, Skipped or Paused.
  final String state;
  final bool canChange;
  final String? skipId;

  bool get hasInterior => services.contains('Cleaning-Internal');

  factory UpcomingDayDto.fromJson(Map<String, dynamic> j) => UpcomingDayDto(
    date: _date(j['date']),
    services: [for (final s in j['services'] as List) s as String],
    state: j['state'] as String,
    canChange: j['can_change'] as bool,
    skipId: j['skip_id'] as String?,
  );
}

class PaymentDto {
  const PaymentDto({
    required this.id,
    required this.kind,
    required this.description,
    required this.amountRupees,
    required this.status,
    required this.dueDate,
    this.invoiceNumber,
    this.daysToDue = 0,
    this.statusMessage = '',
    this.lastPaymentFailed = false,
    this.cycleStart,
    this.cycleEnd,
  });

  final String id;

  /// Plan or Add-on.
  final String kind;
  final String description;
  final int amountRupees;

  /// Not Due, Due, Due today, Over due, Initiated or Paid (PAY-09).
  final String status;
  final DateTime dueDate;
  final String? invoiceNumber;

  /// Negative when over due. The backend works it out (PAY-14).
  final int daysToDue;

  /// "Due in 3 days", "2 days over due", "Waiting for Priveo to confirm",
  /// "Payment received"; empty for Not Due.
  final String statusMessage;

  /// The last payment was rejected by the admin (PAY-17).
  final bool lastPaymentFailed;
  final DateTime? cycleStart;
  final DateTime? cycleEnd;

  /// A payment the customer can still start: it is not Initiated or Paid.
  bool get canMarkPaid => status != 'Initiated' && status != 'Paid';

  /// Due, Due today or Over due: worth a payment line (PAY-18).
  bool get needsPayment =>
      status == 'Due' || status == 'Due today' || status == 'Over due';

  factory PaymentDto.fromJson(Map<String, dynamic> j) => PaymentDto(
    id: j['id'] as String,
    kind: j['kind'] as String,
    description: j['description'] as String,
    amountRupees: j['amount_rupees'] as int,
    status: j['status'] as String,
    dueDate: _date(j['due_date']),
    invoiceNumber: j['invoice_number'] as String?,
    daysToDue: j['days_to_due'] as int? ?? 0,
    statusMessage: j['status_message'] as String? ?? '',
    lastPaymentFailed: j['last_payment_failed'] as bool? ?? false,
    cycleStart: _dateOrNull(j['cycle_start']),
    cycleEnd: _dateOrNull(j['cycle_end']),
  );
}

class PayInstructionsDto {
  const PayInstructionsDto({
    required this.amountRupees,
    required this.upiId,
    required this.payeeName,
    this.qrUrl,
    this.upiUri = '',
  });

  final int amountRupees;
  final String upiId;
  final String payeeName;
  final String? qrUrl;
  final String upiUri;

  factory PayInstructionsDto.fromJson(Map<String, dynamic> j) =>
      PayInstructionsDto(
        amountRupees: j['amount_rupees'] as int,
        upiId: j['upi_id'] as String,
        payeeName: j['payee_name'] as String,
        qrUrl: j['qr_url'] as String?,
        upiUri: j['upi_uri'] as String? ?? '',
      );
}

class PaymentDetailDto {
  const PaymentDetailDto({required this.payment, required this.instructions,
    this.vehicle = '', this.serviceDetails = const {}});

  final PaymentDto payment;
  final PayInstructionsDto instructions;
  final String vehicle;
  final Map<String, dynamic> serviceDetails;

  factory PaymentDetailDto.fromJson(Map<String, dynamic> j) => PaymentDetailDto(
    vehicle: j['vehicle'] as String? ?? '',
    serviceDetails: (j['service_details'] as Map?)?.cast<String, dynamic>() ?? const {},
    payment: PaymentDto.fromJson(j['payment'] as Map<String, dynamic>),
    instructions: PayInstructionsDto.fromJson(
      j['instructions'] as Map<String, dynamic>,
    ),
  );
}

class SubscriptionDto {
  const SubscriptionDto({
    required this.vehicleId,
    required this.planName,
    required this.vehicle,
    required this.registration,
    required this.society,
    required this.status,
    required this.monthlyPriceRupees,
    required this.paymentMethod,
    required this.cutoffTime,
    required this.interiorDay,
    this.startDate,
    this.planInclusions = const [],
    this.planListPriceRupees,
    this.planCode,
    required this.cycleStart,
    this.renewalDate,
    this.expiresOn,
    required this.cycleDays,
    this.daysLeft,
    this.cycleEnd,
    this.inactiveBy,
    this.paymentId,
    this.paymentStatus = 'Not Due',
    this.daysToDue = 0,
    this.statusMessage = '',
    this.lastPaymentFailed = false,
    required this.latestPayment,
    required this.canPayNext,
  });

  final String vehicleId;
  final String? planName;
  final String vehicle;
  final String registration;
  final String society;

  /// Active, Activating, Paused or Inactive (SUB-05).
  final String status;
  final int monthlyPriceRupees;
  final String paymentMethod;
  final String? cutoffTime;
  final String? interiorDay;
  /// The first day the subscription covers.
  final DateTime? startDate;
  final List<String> planInclusions;
  final int? planListPriceRupees;
  final String? planCode;
  final DateTime cycleStart;

  /// The dates below are null unless the payment is Over due (SUB-01).
  final DateTime? renewalDate;
  final DateTime? expiresOn;
  final DateTime? cycleEnd;

  /// The date the subscription becomes Inactive if still unpaid.
  final DateTime? inactiveBy;
  final int cycleDays;
  final int? daysLeft;

  /// The payment of the current cycle, and its display status (PAY-09).
  final String? paymentId;
  final String paymentStatus;
  final int daysToDue;
  final String statusMessage;
  final bool lastPaymentFailed;

  bool get isOverdue => paymentStatus == 'Over due';

  /// The last day of the cycle, worked out from its start and length. Only for
  /// logic (calendar coverage, the ring); it is never shown unless Over due.
  DateTime get coveredUntil => DateTime(
      cycleStart.year, cycleStart.month, cycleStart.day + cycleDays - 1);
  final PaymentDto? latestPayment;
  final bool canPayNext;

  factory SubscriptionDto.fromJson(Map<String, dynamic> j) => SubscriptionDto(
    vehicleId: j['vehicle_id'] as String,
    planName: j['plan_name'] as String?,
    vehicle: j['vehicle'] as String,
    registration: j['registration'] as String,
    society: j['society'] as String,
    status: j['status'] as String,
    monthlyPriceRupees: j['monthly_price_rupees'] as int,
    paymentMethod: j['payment_method'] as String,
    cutoffTime: j['cutoff_time'] as String?,
    interiorDay: j['interior_day'] as String?,
    startDate: j['start_date'] == null ? null : _date(j['start_date']),
    planInclusions: [for (final i in (j['plan_inclusions'] as List? ?? const [])) i as String],
    planListPriceRupees: j['plan_list_price_rupees'] as int?,
    planCode: j['plan_code'] as String?,
    cycleStart: _date(j['cycle_start']),
    renewalDate: _dateOrNull(j['renewal_date']),
    expiresOn: _dateOrNull(j['expires_on']),
    cycleDays: j['cycle_days'] as int,
    daysLeft: j['days_left'] as int?,
    cycleEnd: _dateOrNull(j['cycle_end']),
    inactiveBy: _dateOrNull(j['inactive_by']),
    paymentId: j['payment_id'] as String?,
    paymentStatus: j['payment_status'] as String? ?? 'Not Due',
    daysToDue: j['days_to_due'] as int? ?? 0,
    statusMessage: j['status_message'] as String? ?? '',
    lastPaymentFailed: j['last_payment_failed'] as bool? ?? false,
    latestPayment: j['latest_payment'] == null
        ? null
        : PaymentDto.fromJson(j['latest_payment'] as Map<String, dynamic>),
    canPayNext: j['can_pay_next'] as bool,
  );
}

class InvoiceDto {
  const InvoiceDto({
    required this.number,
    required this.issuedOn,
    required this.amountRupees,
    required this.description,
    required this.customerName,
    required this.sellerName,
    required this.sellerGstin,
    this.taxDetails,
  });

  final String number;
  final DateTime issuedOn;
  final int amountRupees;
  final String description;
  final String customerName;
  final String sellerName;
  final String sellerGstin;
  final Map<String, dynamic>? taxDetails;

  factory InvoiceDto.fromJson(Map<String, dynamic> j) => InvoiceDto(
    number: j['number'] as String,
    issuedOn: _date(j['issued_on']),
    amountRupees: j['amount_rupees'] as int,
    description: j['description'] as String,
    customerName: j['customer_name'] as String,
    sellerName: j['seller_name'] as String,
    sellerGstin: j['seller_gstin'] as String,
    taxDetails: (j['tax_details'] as Map?)?.cast<String, dynamic>(),
  );
}

class AddonOfferDto {
  const AddonOfferDto({
    this.code = '',
    required this.service,
    required this.name,
    required this.description,
    required this.priceRupees,
    required this.listPriceRupees,
    required this.durationMinutes,
  });

  /// The catalogue ID (ADN-0002) that tells add-ons apart; empty for the built-in one.
  final String code;
  final String service;
  final String name;
  final String description;
  final int priceRupees;
  final int? listPriceRupees;
  final int durationMinutes;

  factory AddonOfferDto.fromJson(Map<String, dynamic> j) => AddonOfferDto(
    code: j['code'] as String? ?? '',
    service: j['service'] as String,
    name: j['name'] as String,
    description: j['description'] as String,
    priceRupees: j['price_rupees'] as int,
    listPriceRupees: j['list_price_rupees'] as int?,
    durationMinutes: j['duration_minutes'] as int,
  );
}

class AddonRequestDto {
  const AddonRequestDto({
    required this.id,
    required this.service,
    this.addonName = '',
    required this.standalone,
    required this.date,
    required this.finishBy,
    required this.status,
    required this.priceRupees,
    required this.paymentId,
    required this.paymentStatus,
    required this.canChange,
    this.changeRequested = false,
    this.requestedDate,
    this.requestedFinishBy,
    this.crewName,
    this.startTime,
    this.visitId,
    this.vehicleId,
  });

  final String id;
  final String service;

  /// What the customer bought, as the catalogue named it.
  final String addonName;
  final bool standalone;
  final DateTime date;
  final String finishBy;

  /// What to call it on screen.
  String get title => addonName.isEmpty ? service : addonName;

  /// Requested, Scheduled, Completed, Cancelled or Missed (ADD-07).
  final String status;
  final int? priceRupees;
  final String? paymentId;
  final String? paymentStatus;
  final bool canChange;
  final bool changeRequested;
  final DateTime? requestedDate;
  final String? requestedFinishBy, crewName, startTime, visitId, vehicleId;

  factory AddonRequestDto.fromJson(Map<String, dynamic> j) => AddonRequestDto(
    id: j['id'] as String,
    service: j['service'] as String,
    addonName: j['addon_name'] as String? ?? '',
    standalone: j['standalone'] as bool,
    date: _date(j['date']),
    finishBy: j['finish_by'] as String,
    status: j['status'] as String,
    priceRupees: j['price_rupees'] as int?,
    paymentId: j['payment_id'] as String?,
    paymentStatus: j['payment_status'] as String?,
    canChange: j['can_change'] as bool,
    changeRequested: j['change_requested'] as bool? ?? false,
    requestedDate: j['requested_date'] == null
        ? null
        : _date(j['requested_date']),
    requestedFinishBy: j['requested_finish_by'] as String?,
    crewName: j['crew_name'] as String?,
    startTime: j['start_time'] as String?,
    visitId: j['visit_id'] as String?,
    vehicleId: j['vehicle_id'] as String?,
  );
}

class AddonsDto {
  const AddonsDto({required this.offers, required this.requests});

  final List<AddonOfferDto> offers;
  final List<AddonRequestDto> requests;

  factory AddonsDto.fromJson(Map<String, dynamic> j) => AddonsDto(
    offers: [
      for (final o in j['offers'] as List)
        AddonOfferDto.fromJson(o as Map<String, dynamic>),
    ],
    requests: [
      for (final o in j['requests'] as List)
        AddonRequestDto.fromJson(o as Map<String, dynamic>),
    ],
  );
}
