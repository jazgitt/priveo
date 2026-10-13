import '../../../core/network/read_refresh.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

class AdminAlert {
  const AdminAlert({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    required this.createdAt,
    required this.read,
    this.refType,
    this.refId,
  });

  final String id;
  final String kind;
  final String title;
  final String body;
  final DateTime createdAt;
  final bool read;
  final String? refType;
  final String? refId;

  factory AdminAlert.fromJson(Map<String, dynamic> j) => AdminAlert(
    id: j['id'] as String,
    kind: j['kind'] as String,
    title: j['title'] as String,
    body: (j['body'] as String?) ?? '',
    createdAt: DateTime.parse(j['created_at'] as String),
    read: j['read'] as bool,
    refType: j['ref_type'] as String?,
    refId: j['ref_id'] as String?,
  );
}

class AlertList {
  const AlertList({required this.unreadCount, required this.items});

  final int unreadCount;
  final List<AdminAlert> items;

  factory AlertList.fromJson(Map<String, dynamic> j) => AlertList(
    unreadCount: j['unread_count'] as int,
    items: [
      for (final e in (j['items'] as List))
        AdminAlert.fromJson(e as Map<String, dynamic>),
    ],
  );
}

abstract class AlertsRepository {
  Future<AlertList> list();
  Future<void> markRead(String id);
  Future<void> markAllRead();
}

class ApiAlertsRepository implements AlertsRepository {
  ApiAlertsRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() send) async {
    try {
      return await send();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<AlertList> list() => _call(() async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/admin/alerts');
    return AlertList.fromJson(r.data!);
  });

  @override
  Future<void> markRead(String id) =>
      _call(() => _dio.post<dynamic>('/v1/admin/alerts/$id/read'));

  @override
  Future<void> markAllRead() =>
      _call(() => _dio.post<dynamic>('/v1/admin/alerts/read-all'));
}

final alertsRepositoryProvider = Provider<AlertsRepository>(
  (ref) => ApiAlertsRepository((ref.watch(readRefreshProvider), ref.watch(dioProvider)).$2),
);

final alertsProvider = FutureProvider.autoDispose<AlertList>(
  (ref) => ref.watch(alertsRepositoryProvider).list(),
);
