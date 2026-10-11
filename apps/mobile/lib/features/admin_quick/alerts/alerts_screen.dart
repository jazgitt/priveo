import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../support/support_strings.dart';
import '../../support/widgets.dart';
import 'alerts_data.dart';

/// The admin's alert list with the unread count (ADM-ACC-09, ADM-ACC-07).
/// Tapping an alert marks it read.
class AlertsScreen extends ConsumerWidget {
  const AlertsScreen({super.key});

  Future<void> _run(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function() call,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await call();
      ref.invalidate(alertsProvider);
    } catch (e) {
      if (context.mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text(failureText(context, e))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alerts = ref.watch(alertsProvider);
    final repo = ref.watch(alertsRepositoryProvider);
    final unread = alerts.value?.unreadCount ?? 0;
    return Scaffold(
      appBar: AppBar(
        title: Text(t('support_alerts_title')),
        actions: [
          if (unread > 0)
            TextButton(
              onPressed: () => _run(context, ref, repo.markAllRead),
              child: Text(t('support_alerts_mark_all')),
            ),
        ],
      ),
      body: alerts.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(context, e),
          onRetry: () => ref.invalidate(alertsProvider),
        ),
        data: (list) => RefreshIndicator(
          onRefresh: () => ref.refresh(alertsProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                t('support_alerts_unread', {'count': list.unreadCount}),
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              if (list.items.isEmpty) Text(t('support_alerts_empty')),
              for (final a in list.items)
                Card(
                  child: ListTile(
                    leading: Icon(
                      a.read
                          ? Symbols.notifications_rounded
                          : Symbols.notifications_active_rounded,
                    ),
                    title: Text(
                      a.title,
                      style: TextStyle(
                        fontWeight: a.read ? FontWeight.w400 : FontWeight.w700,
                      ),
                    ),
                    subtitle: Text(
                      [
                        if (a.body.isNotEmpty) a.body,
                        formatDate(a.createdAt.toLocal()),
                      ].join('\n'),
                    ),
                    isThreeLine: a.body.isNotEmpty,
                    onTap: a.read
                        ? null
                        : () => _run(context, ref, () => repo.markRead(a.id)),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
