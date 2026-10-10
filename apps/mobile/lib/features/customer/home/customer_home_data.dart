import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../../core/util/format.dart';

class QuickAction {
  const QuickAction(this.key, this.label);
  final String key;
  final String label;
}

class CustomerHome {
  const CustomerHome({
    required this.greetingName,
    required this.registration,
    required this.model,
    required this.society,
    required this.parking,
    required this.nextServiceDate,
    required this.nextServiceName,
    required this.nextServiceStatus,
    required this.subscriptionStatus,
    required this.quickActions,
  });

  final String greetingName;
  final String registration;
  final String model;
  final String society;
  final String parking;
  final DateTime nextServiceDate;
  final String nextServiceName;
  final String nextServiceStatus;
  final String subscriptionStatus;
  final List<QuickAction> quickActions;

  factory CustomerHome.fromJson(Map<String, dynamic> j) {
    final v = j['vehicle'] as Map<String, dynamic>;
    final n = j['next_service'] as Map<String, dynamic>;
    return CustomerHome(
      greetingName: j['greeting_name'] as String,
      registration: v['registration'] as String,
      model: v['model'] as String,
      society: v['society'] as String,
      parking: v['parking'] as String,
      nextServiceDate: parseApiDate(n['date'] as String),
      nextServiceName: n['service'] as String,
      nextServiceStatus: n['status'] as String,
      subscriptionStatus: j['subscription_status'] as String,
      quickActions: [
        for (final a in j['quick_actions'] as List)
          QuickAction((a as Map)['key'] as String, a['label'] as String),
      ],
    );
  }
}

abstract class CustomerHomeRepository {
  Future<CustomerHome> fetch();
}

class ApiCustomerHomeRepository implements CustomerHomeRepository {
  ApiCustomerHomeRepository(this._dio);
  final Dio _dio;

  @override
  Future<CustomerHome> fetch() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/v1/customer/home');
      return CustomerHome.fromJson(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }
}

final customerHomeRepositoryProvider = Provider<CustomerHomeRepository>(
    (ref) => ApiCustomerHomeRepository(ref.watch(dioProvider)));

final customerHomeProvider = FutureProvider.autoDispose<CustomerHome>(
    (ref) => ref.watch(customerHomeRepositoryProvider).fetch());
