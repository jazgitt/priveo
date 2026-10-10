import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

class PaymentToConfirm {
  const PaymentToConfirm({
    required this.id,
    required this.customerLabel,
    required this.amountRupees,
    required this.reference,
  });

  final String id;
  final String customerLabel;
  final int amountRupees;
  final String reference;

  factory PaymentToConfirm.fromJson(Map<String, dynamic> j) => PaymentToConfirm(
        id: j['id'] as String,
        customerLabel: j['customer_label'] as String,
        amountRupees: j['amount_rupees'] as int,
        reference: j['reference'] as String,
      );
}

class AdminHome {
  const AdminHome({
    required this.alertCount,
    required this.payments,
    required this.needsSchedulingCount,
  });

  final int alertCount;
  final List<PaymentToConfirm> payments;
  final int needsSchedulingCount;

  factory AdminHome.fromJson(Map<String, dynamic> j) => AdminHome(
        alertCount: j['alert_count'] as int,
        needsSchedulingCount: j['needs_scheduling_count'] as int,
        payments: [
          for (final x in j['payments_to_confirm'] as List)
            PaymentToConfirm.fromJson(x as Map<String, dynamic>),
        ],
      );
}

abstract class AdminHomeRepository {
  Future<AdminHome> fetch();
}

class ApiAdminHomeRepository implements AdminHomeRepository {
  ApiAdminHomeRepository(this._dio);
  final Dio _dio;

  @override
  Future<AdminHome> fetch() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/v1/admin/home');
      return AdminHome.fromJson(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }
}

final adminHomeRepositoryProvider = Provider<AdminHomeRepository>(
    (ref) => ApiAdminHomeRepository(ref.watch(dioProvider)));

final adminHomeProvider = FutureProvider.autoDispose<AdminHome>(
    (ref) => ref.watch(adminHomeRepositoryProvider).fetch());
