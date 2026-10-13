import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

/// One notification switch (SET-02).
class NotificationPrefDto {
  const NotificationPrefDto({
    required this.event,
    required this.title,
    required this.description,
    required this.enabled,
  });

  final String event;
  final String title;
  final String description;
  final bool enabled;

  factory NotificationPrefDto.fromJson(Map<String, dynamic> j) =>
      NotificationPrefDto(
        event: j['event'] as String,
        title: j['title'] as String,
        description: j['description'] as String,
        enabled: j['enabled'] as bool,
      );

  NotificationPrefDto withEnabled(bool value) => NotificationPrefDto(
    event: event,
    title: title,
    description: description,
    enabled: value,
  );
}

/// The customer's notification switches. Failures are thrown as
/// [ApiFailure]. Tests override [notificationPrefsRepositoryProvider].
abstract class NotificationPrefsRepository {
  Future<List<NotificationPrefDto>> load();
  Future<List<NotificationPrefDto>> set(String event, bool enabled);
}

class DioNotificationPrefsRepository implements NotificationPrefsRepository {
  DioNotificationPrefsRepository(this._dio);

  final Dio _dio;

  static const _path = '/v1/customer/notification-preferences';

  List<NotificationPrefDto> _items(Map<String, dynamic> body) => [
    for (final e in body['items'] as List<dynamic>)
      NotificationPrefDto.fromJson(e as Map<String, dynamic>),
  ];

  @override
  Future<List<NotificationPrefDto>> load() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(_path);
      return _items(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<List<NotificationPrefDto>> set(String event, bool enabled) async {
    try {
      final r = await _dio.put<Map<String, dynamic>>(
        _path,
        data: {
          'items': [
            {'event': event, 'enabled': enabled},
          ],
        },
      );
      return _items(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }
}

final notificationPrefsRepositoryProvider =
    Provider<NotificationPrefsRepository>(
      (ref) => DioNotificationPrefsRepository(ref.watch(dioProvider)),
    );

final notificationPrefsProvider =
    FutureProvider.autoDispose<List<NotificationPrefDto>>(
      (ref) => ref.watch(notificationPrefsRepositoryProvider).load(),
    );
