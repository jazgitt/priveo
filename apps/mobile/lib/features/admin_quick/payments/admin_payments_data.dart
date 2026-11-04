import '../../../core/network/read_refresh.dart';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

/// A payment as the admin sees it (ADM-PAY-01).
class AdminPaymentDto {
  const AdminPaymentDto({
    required this.id,
    required this.kind,
    required this.description,
    required this.amountRupees,
    required this.status,
    required this.dueDate,
    required this.customerName,
    required this.flat,
    required this.vehicle,
    this.daysToDue = 0,
    this.statusMessage = '',
    this.lastPaymentFailed = false,
  });

  final String id;
  final String kind;
  final String description;
  final int amountRupees;
  final String status;
  final DateTime dueDate;
  final String customerName;
  final String flat;
  final String vehicle;

  /// Not Due, Due, Due today, Over due, Initiated or Paid (ADM-PAY-01).
  final int daysToDue;
  final String statusMessage;
  final bool lastPaymentFailed;

  factory AdminPaymentDto.fromJson(Map<String, dynamic> j) => AdminPaymentDto(
    id: j['id'] as String,
    kind: j['kind'] as String,
    description: j['description'] as String,
    amountRupees: j['amount_rupees'] as int,
    status: j['status'] as String,
    dueDate: DateTime.parse(j['due_date'] as String),
    customerName: j['customer_name'] as String,
    flat: j['flat'] as String,
    vehicle: j['vehicle'] as String,
    daysToDue: j['days_to_due'] as int? ?? 0,
    statusMessage: j['status_message'] as String? ?? '',
    lastPaymentFailed: j['last_payment_failed'] as bool? ?? false,
  );
}

class AdminAlertDto {
  const AdminAlertDto({
    required this.id,
    required this.kind,
    required this.message,
    required this.createdAt,
    required this.read,
  });

  final String id;
  final String kind;
  final String message;
  final DateTime createdAt;
  final bool read;

  factory AdminAlertDto.fromJson(Map<String, dynamic> j) => AdminAlertDto(
    id: j['id'] as String,
    kind: j['kind'] as String,
    message: j['message'] as String,
    createdAt: DateTime.parse(j['created_at'] as String),
    read: j['read'] as bool,
  );
}

/// The admin's quick actions for money (ADM-ACC-07 b). They call the same
/// admin routes as the web portal (ADM-ACC-10).
abstract class AdminPaymentsRepository {
  /// Payments with the given status, or all of them when [status] is null.
  Future<List<AdminPaymentDto>> payments({String? status});
  Future<void> confirm(String paymentId);
  Future<void> reject(String paymentId);
  Future<List<AdminAlertDto>> alerts();
  Future<void> markRead(String alertId);
}

class DioAdminPaymentsRepository implements AdminPaymentsRepository {
  DioAdminPaymentsRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(
    Future<Response<dynamic>> Function() send,
    T Function(dynamic data) read,
  ) async {
    try {
      return read((await send()).data);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<List<AdminPaymentDto>> payments({String? status}) => _call(
    () => _dio.get<dynamic>(
      '/v1/admin/payments',
      queryParameters: {'status': ?status},
    ),
    (d) => [
      for (final x in d as List)
        AdminPaymentDto.fromJson(x as Map<String, dynamic>),
    ],
  );

  @override
  Future<void> confirm(String id) =>
      _call(() => _dio.post<dynamic>('/v1/admin/payments/$id/confirm'), (_) {});

  @override
  Future<void> reject(String id) =>
      _call(() => _dio.post<dynamic>('/v1/admin/payments/$id/reject'), (_) {});

  @override
  Future<List<AdminAlertDto>> alerts() => _call(
    () => _dio.get<dynamic>('/v1/admin/payment-alerts'),
    (d) => [
      for (final x in d as List)
        AdminAlertDto.fromJson(x as Map<String, dynamic>),
    ],
  );

  @override
  Future<void> markRead(String id) => _call(
    () => _dio.post<dynamic>('/v1/admin/payment-alerts/$id/read'),
    (_) {},
  );
}

final adminPaymentsRepositoryProvider = Provider<AdminPaymentsRepository>(
  (ref) => DioAdminPaymentsRepository(
    (ref.watch(readRefreshProvider), ref.watch(dioProvider)).$2,
  ),
);

/// The statuses the admin can filter by; null is all of them.
const adminPaymentStatuses = [
  'Initiated',
  'Over due',
  'Due today',
  'Due',
  'Not Due',
  'Paid',
];

final adminPaymentsProvider = FutureProvider.autoDispose
    .family<List<AdminPaymentDto>, String?>(
      (ref, status) =>
          ref.watch(adminPaymentsRepositoryProvider).payments(status: status),
    );

final adminAlertsProvider = FutureProvider.autoDispose<List<AdminAlertDto>>(
  (ref) => ref.watch(adminPaymentsRepositoryProvider).alerts(),
);
