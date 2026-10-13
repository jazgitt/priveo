import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../../core/ui/widgets.dart';
import '../crew_ui.dart';

/// Words of the crew inbox (CRW-NOT-01 to CRW-NOT-05).
abstract final class CrewNotificationText {
  static const title = 'Notifications';
  static const tooltip = 'Notifications';
  static const empty = 'No notifications yet.';
  static const markAll = 'Mark all as read';
}

class CrewNotificationDto {
  const CrewNotificationDto({
    required this.id,
    required this.event,
    required this.title,
    required this.body,
    required this.createdAt,
    required this.read,
  });

  final String id;

  /// `crew_schedule_frozen`, `crew_job_removed`, `crew_job_assigned` or
  /// `crew_job_reassigned`.
  final String event;
  final String title;
  final String body;
  final DateTime createdAt;
  final bool read;

  factory CrewNotificationDto.fromJson(Map<String, dynamic> j) =>
      CrewNotificationDto(
        id: j['id'] as String,
        event: j['event'] as String,
        title: j['title'] as String,
        body: j['body'] as String,
        createdAt: DateTime.parse(j['created_at'] as String).toLocal(),
        read: j['read'] as bool,
      );
}

class CrewInbox {
  const CrewInbox({required this.unreadCount, required this.items});

  final int unreadCount;
  final List<CrewNotificationDto> items;

  factory CrewInbox.fromJson(Map<String, dynamic> j) => CrewInbox(
    unreadCount: j['unread_count'] as int,
    items: [
      for (final e in j['items'] as List<dynamic>)
        CrewNotificationDto.fromJson(e as Map<String, dynamic>),
    ],
  );
}

/// The crew's inbox. Tests override [crewInboxRepositoryProvider].
abstract class CrewInboxRepository {
  Future<CrewInbox> inbox();
  Future<void> markRead(String id);
  Future<void> markAllRead();
}

class DioCrewInboxRepository implements CrewInboxRepository {
  DioCrewInboxRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() f) async {
    try {
      return await f();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<CrewInbox> inbox() => _call(() async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/crew/notifications');
    return CrewInbox.fromJson(r.data!);
  });

  @override
  Future<void> markRead(String id) =>
      _call(() => _dio.post<void>('/v1/crew/notifications/$id/read'));

  @override
  Future<void> markAllRead() =>
      _call(() => _dio.post<void>('/v1/crew/notifications/read-all'));
}

final crewInboxRepositoryProvider = Provider<CrewInboxRepository>(
  (ref) => DioCrewInboxRepository(ref.watch(dioProvider)),
);

final crewInboxProvider = FutureProvider.autoDispose<CrewInbox>(
  (ref) => ref.watch(crewInboxRepositoryProvider).inbox(),
);

/// The crew's notifications. No switches: the crew cannot turn these off
/// (CRW-NOT-03). A message holds no customer name or mobile number.
class CrewNotificationsScreen extends ConsumerWidget {
  const CrewNotificationsScreen({super.key});

  static IconData _icon(String event) => switch (event) {
    'crew_schedule_frozen' => Symbols.event_available_rounded,
    'crew_job_removed' => Symbols.event_busy_rounded,
    'crew_job_assigned' => Symbols.assignment_add_rounded,
    'crew_job_reassigned' => Symbols.swap_horiz_rounded,
    _ => Symbols.notifications_rounded,
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final inbox = ref.watch(crewInboxProvider);
    Future<void> markAll() async {
      await ref.read(crewInboxRepositoryProvider).markAllRead();
      ref.invalidate(crewInboxProvider);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text(CrewNotificationText.title),
        actions: [
          if ((inbox.value?.unreadCount ?? 0) > 0)
            TextButton(
              onPressed: markAll,
              child: const Text(CrewNotificationText.markAll),
            ),
        ],
      ),
      body: inbox.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(crewInboxProvider),
        ),
        data: (data) {
          if (data.items.isEmpty) {
            return const Center(child: Text(CrewNotificationText.empty));
          }
          return RefreshIndicator(
            onRefresh: () => ref.refresh(crewInboxProvider.future),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: data.items.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, i) {
                final n = data.items[i];
                return Card(
                  child: ListTile(
                    leading: Icon(_icon(n.event)),
                    title: Text(
                      n.title,
                      style: text.titleSmall?.copyWith(
                        fontWeight: n.read ? FontWeight.w500 : FontWeight.w800,
                      ),
                    ),
                    subtitle: Text(
                      '${n.body}\n'
                      '${DateFormat('dd-MMM-yy, h:mm a').format(n.createdAt)}',
                    ),
                    isThreeLine: true,
                    onTap: () async {
                      if (n.read) return;
                      await ref
                          .read(crewInboxRepositoryProvider)
                          .markRead(n.id);
                      ref.invalidate(crewInboxProvider);
                    },
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
