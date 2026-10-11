import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

// Hand-written DTOs for the customer read endpoints (/v1/customer/...).
// They move to the generated client when the contract is regenerated.

DateTime _day(Object? v) => DateTime.parse(v as String);

List<T> _list<T>(Object? v, T Function(Map<String, dynamic>) f) => [
  for (final e in (v as List<dynamic>)) f(e as Map<String, dynamic>),
];

class CalendarVisit {
  const CalendarVisit({
    required this.visitId,
    required this.vehicleId,
    required this.date,
    required this.status,
    required this.services,
  });

  final String visitId;
  final String vehicleId;
  final DateTime date;

  /// Scheduled, In progress, Completed, Skipped or Missed.
  final String status;
  final List<String> services;

  factory CalendarVisit.fromJson(Map<String, dynamic> j) => CalendarVisit(
    visitId: j['visit_id'] as String,
    vehicleId: j['vehicle_id'] as String,
    date: _day(j['date']),
    status: j['status'] as String,
    services: [for (final s in j['services'] as List<dynamic>) s as String],
  );
}

class CalendarMonthDto {
  const CalendarMonthDto({required this.month, required this.visits});

  final String month;
  final List<CalendarVisit> visits;

  factory CalendarMonthDto.fromJson(Map<String, dynamic> j) => CalendarMonthDto(
    month: j['month'] as String,
    visits: _list(j['visits'], CalendarVisit.fromJson),
  );
}

class NextServiceDto {
  const NextServiceDto({
    required this.vehicleId,
    required this.visitId,
    required this.date,
    required this.service,
    required this.status,
  });

  final String vehicleId;
  final String visitId;
  final DateTime date;
  final String service;
  final String status;

  factory NextServiceDto.fromJson(Map<String, dynamic> j) => NextServiceDto(
    vehicleId: j['vehicle_id'] as String,
    visitId: j['visit_id'] as String,
    date: _day(j['date']),
    service: j['service'] as String,
    status: j['status'] as String,
  );
}

class ProofDto {
  const ProofDto({required this.kind, required this.url});

  /// `photo` or `video`.
  final String kind;
  final String url;

  bool get isVideo => kind == 'video';

  factory ProofDto.fromJson(Map<String, dynamic> j) =>
      ProofDto(kind: j['kind'] as String, url: j['url'] as String);
}

class JobDto {
  const JobDto({
    required this.id,
    required this.service,
    required this.status,
    required this.proof,
  });

  final String id;
  final String service;
  final String status;
  final List<ProofDto> proof;

  factory JobDto.fromJson(Map<String, dynamic> j) => JobDto(
    id: j['id'] as String,
    service: j['service'] as String,
    status: j['status'] as String,
    proof: _list(j['proof'], ProofDto.fromJson),
  );
}

class VisitDetailDto {
  const VisitDetailDto({
    required this.id,
    required this.vehicleId,
    required this.vehicleRegistration,
    required this.vehicleModel,
    required this.date,
    required this.status,
    required this.jobs,
  });

  final String id;
  final String vehicleId;
  final String vehicleRegistration;
  final String vehicleModel;
  final DateTime date;
  final String status;
  final List<JobDto> jobs;

  /// Every photo and video of the visit, in job order.
  List<ProofDto> get proof => [for (final j in jobs) ...j.proof];

  factory VisitDetailDto.fromJson(Map<String, dynamic> j) => VisitDetailDto(
    id: j['id'] as String,
    vehicleId: j['vehicle_id'] as String,
    vehicleRegistration: j['vehicle_registration'] as String,
    vehicleModel: j['vehicle_model'] as String,
    date: _day(j['date']),
    status: j['status'] as String,
    jobs: _list(j['jobs'], JobDto.fromJson),
  );
}

class HistoryItemDto {
  const HistoryItemDto({
    required this.visitId,
    required this.vehicleId,
    required this.date,
    required this.status,
    required this.services,
    required this.photoCount,
  });

  final String visitId;
  final String vehicleId;
  final DateTime date;
  final String status;
  final List<String> services;
  final int photoCount;

  factory HistoryItemDto.fromJson(Map<String, dynamic> j) => HistoryItemDto(
    visitId: j['visit_id'] as String,
    vehicleId: j['vehicle_id'] as String,
    date: _day(j['date']),
    status: j['status'] as String,
    services: [for (final s in j['services'] as List<dynamic>) s as String],
    photoCount: j['photo_count'] as int,
  );
}

class VehicleSummaryDto {
  const VehicleSummaryDto({
    required this.id,
    required this.registration,
    required this.model,
    required this.society,
    required this.subscriptionStatus,
  });

  final String id;
  final String registration;
  final String model;
  final String society;
  final String? subscriptionStatus;

  factory VehicleSummaryDto.fromJson(Map<String, dynamic> j) =>
      VehicleSummaryDto(
        id: j['id'] as String,
        registration: j['registration'] as String,
        model: j['model'] as String,
        society: j['society'] as String,
        subscriptionStatus: j['subscription_status'] as String?,
      );
}

class VehicleDetailDto extends VehicleSummaryDto {
  const VehicleDetailDto({
    required super.id,
    required super.registration,
    required super.model,
    required super.society,
    required super.subscriptionStatus,
    required this.make,
    required this.variant,
    required this.category,
    required this.parking,
    required this.monthlyPriceRupees,
    required this.cutoffTime,
    required this.interiorDay,
  });

  final String make;
  final String variant;
  final String category;
  final String parking;
  final int? monthlyPriceRupees;
  final String? cutoffTime;
  final String? interiorDay;

  factory VehicleDetailDto.fromJson(Map<String, dynamic> j) => VehicleDetailDto(
    id: j['id'] as String,
    registration: j['registration'] as String,
    model: j['model'] as String,
    society: j['society'] as String,
    subscriptionStatus: j['subscription_status'] as String?,
    make: j['make'] as String,
    variant: j['variant'] as String,
    category: j['category'] as String,
    parking: j['parking'] as String,
    monthlyPriceRupees: j['monthly_price_rupees'] as int?,
    cutoffTime: j['cutoff_time'] as String?,
    interiorDay: j['interior_day'] as String?,
  );
}

class NotificationDto {
  const NotificationDto({
    required this.id,
    required this.event,
    required this.title,
    required this.body,
    required this.visitId,
    required this.createdAt,
    required this.read,
    this.refType,
    this.refId,
  });

  final String id;
  final String event;
  final String title;
  final String body;
  final String? visitId;

  /// What a tap opens besides a visit: `payment`, `complaint` or `checkin`,
  /// with its ID.
  final String? refType;
  final String? refId;
  final DateTime createdAt;
  final bool read;

  factory NotificationDto.fromJson(Map<String, dynamic> j) => NotificationDto(
    id: j['id'] as String,
    event: j['event'] as String,
    title: j['title'] as String,
    body: j['body'] as String,
    visitId: j['visit_id'] as String?,
    refType: j['ref_type'] as String?,
    refId: j['ref_id'] as String?,
    createdAt: DateTime.parse(j['created_at'] as String).toLocal(),
    read: j['read'] as bool,
  );
}

class InboxDto {
  const InboxDto({required this.unreadCount, required this.items});

  final int unreadCount;
  final List<NotificationDto> items;

  factory InboxDto.fromJson(Map<String, dynamic> j) => InboxDto(
    unreadCount: j['unread_count'] as int,
    items: _list(j['items'], NotificationDto.fromJson),
  );
}

/// The customer's reads. Failures are thrown as [ApiFailure]. Tests override
/// [customerReadsProvider] with a fake.
abstract class CustomerReadsRepository {
  Future<CalendarMonthDto> calendar(String month, {String? vehicleId});
  Future<List<NextServiceDto>> nextServices();
  Future<VisitDetailDto> visit(String visitId);
  Future<List<HistoryItemDto>> history({String? vehicleId, int offset = 0});
  Future<List<VehicleSummaryDto>> vehicles();
  Future<VehicleDetailDto> vehicle(String vehicleId);
  Future<InboxDto> inbox();
  Future<void> markRead(String notificationId);
  Future<void> markAllRead();
  Future<void> registerDevice(String token, String platform);
}

class DioCustomerReadsRepository implements CustomerReadsRepository {
  DioCustomerReadsRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() f) async {
    try {
      return await f();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  Future<Map<String, dynamic>> _object(
    String path, {
    Map<String, dynamic>? query,
  }) => _call(() async {
    final r = await _dio.get<Map<String, dynamic>>(
      path,
      queryParameters: query,
    );
    return r.data!;
  });

  Future<List<Map<String, dynamic>>> _array(
    String path, {
    Map<String, dynamic>? query,
  }) => _call(() async {
    final r = await _dio.get<List<dynamic>>(path, queryParameters: query);
    return [for (final e in r.data!) e as Map<String, dynamic>];
  });

  @override
  Future<CalendarMonthDto> calendar(String month, {String? vehicleId}) async =>
      CalendarMonthDto.fromJson(
        await _object(
          '/v1/customer/calendar',
          query: {'month': month, 'vehicle_id': ?vehicleId},
        ),
      );

  @override
  Future<List<NextServiceDto>> nextServices() async => [
    for (final j in await _array('/v1/customer/next-service'))
      NextServiceDto.fromJson(j),
  ];

  @override
  Future<VisitDetailDto> visit(String visitId) async =>
      VisitDetailDto.fromJson(await _object('/v1/customer/visits/$visitId'));

  @override
  Future<List<HistoryItemDto>> history({
    String? vehicleId,
    int offset = 0,
  }) async => [
    for (final j in await _array(
      '/v1/customer/history',
      query: {'offset': offset, 'vehicle_id': ?vehicleId},
    ))
      HistoryItemDto.fromJson(j),
  ];

  @override
  Future<List<VehicleSummaryDto>> vehicles() async => [
    for (final j in await _array('/v1/customer/vehicles'))
      VehicleSummaryDto.fromJson(j),
  ];

  @override
  Future<VehicleDetailDto> vehicle(String vehicleId) async =>
      VehicleDetailDto.fromJson(
        await _object('/v1/customer/vehicles/$vehicleId'),
      );

  @override
  Future<InboxDto> inbox() async =>
      InboxDto.fromJson(await _object('/v1/customer/notifications'));

  @override
  Future<void> markRead(String notificationId) => _call(
    () => _dio.post<void>('/v1/customer/notifications/$notificationId/read'),
  );

  @override
  Future<void> markAllRead() =>
      _call(() => _dio.post<void>('/v1/customer/notifications/read-all'));

  @override
  Future<void> registerDevice(String token, String platform) => _call(
    () => _dio.put<void>(
      '/v1/customer/devices',
      data: {'token': token, 'platform': platform},
    ),
  );
}

final customerReadsProvider = Provider<CustomerReadsRepository>(
  (ref) => DioCustomerReadsRepository(ref.watch(dioProvider)),
);

// Providers for the screens. The Home screen keeps its own in
// features/customer/home/customer_home_data.dart.

/// A failed look-up is an empty list: Home keeps working without it.
final nextServicesProvider = FutureProvider.autoDispose<List<NextServiceDto>>((
  ref,
) async {
  try {
    return await ref.watch(customerReadsProvider).nextServices();
  } catch (_) {
    return const [];
  }
});

final vehiclesProvider = FutureProvider.autoDispose<List<VehicleSummaryDto>>(
  (ref) => ref.watch(customerReadsProvider).vehicles(),
);

final vehicleDetailProvider = FutureProvider.autoDispose
    .family<VehicleDetailDto, String>(
      (ref, id) => ref.watch(customerReadsProvider).vehicle(id),
    );

final visitDetailProvider = FutureProvider.autoDispose
    .family<VisitDetailDto, String>(
      (ref, id) => ref.watch(customerReadsProvider).visit(id),
    );

/// The calendar's month and vehicle, as one key.
typedef CalendarKey = ({String month, String? vehicleId});

final calendarMonthProvider = FutureProvider.autoDispose
    .family<CalendarMonthDto, CalendarKey>(
      (ref, k) => ref
          .watch(customerReadsProvider)
          .calendar(k.month, vehicleId: k.vehicleId),
    );

final historyProvider = FutureProvider.autoDispose
    .family<List<HistoryItemDto>, String?>(
      (ref, vehicleId) =>
          ref.watch(customerReadsProvider).history(vehicleId: vehicleId),
    );

final inboxProvider = FutureProvider.autoDispose<InboxDto>(
  (ref) => ref.watch(customerReadsProvider).inbox(),
);
