import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/theme.dart';
import '../cust_strings.dart';
import '../cust_ui.dart';
import '../data/customer_reads_repository.dart';
import '../visit/visit_details_screen.dart';

/// Opens the inbox over the current screen.
void openNotifications(BuildContext context) {
  Navigator.of(
    context,
  ).push(MaterialPageRoute<void>(builder: (_) => const NotificationsScreen()));
}

/// The in-app inbox (NOTIF-02). Tapping a message marks it read and, when it
/// is about a visit, opens the visit.
class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  static IconData _icon(String event) => switch (event) {
    'service_completed' => Symbols.check_circle_rounded,
    'service_skipped' => Symbols.skip_next_rounded,
    'complaint_update' => Symbols.report_rounded,
    'renewal_reminder' => Symbols.payments_rounded,
    _ => Symbols.notifications_rounded,
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final inbox = ref.watch(inboxProvider);
    Future<void> markAll() async {
      await ref.read(customerReadsProvider).markAllRead();
      ref.invalidate(inboxProvider);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text(CustStrings.notificationsTitle),
        actions: [
          if ((inbox.value?.unreadCount ?? 0) > 0)
            TextButton(
              onPressed: markAll,
              child: const Text(CustStrings.markAllRead),
            ),
        ],
      ),
      body: SafeArea(
        child: AsyncBody<InboxDto>(
          value: inbox,
          onRetry: () => ref.invalidate(inboxProvider),
          builder: (data) {
            if (data.items.isEmpty) {
              return const Center(child: Text(CustStrings.notificationsEmpty));
            }
            return ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: data.items.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, i) {
                final n = data.items[i];
                return Card(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () async {
                      if (!n.read) {
                        await ref.read(customerReadsProvider).markRead(n.id);
                        ref.invalidate(inboxProvider);
                      }
                      if (n.visitId != null && context.mounted) {
                        openVisitDetails(context, n.visitId!);
                      }
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(_icon(n.event), color: n.read ? b.mute : b.gold),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  n.title,
                                  style: text.titleSmall?.copyWith(
                                    fontWeight: n.read
                                        ? FontWeight.w500
                                        : FontWeight.w800,
                                  ),
                                ),
                                if (n.body.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Text(
                                    n.body,
                                    style: text.bodyMedium?.copyWith(
                                      color: b.mute,
                                    ),
                                  ),
                                ],
                                const SizedBox(height: 6),
                                Text(
                                  DateFormat(
                                    'dd-MMM-yy, h:mm a',
                                  ).format(n.createdAt),
                                  style: text.bodySmall?.copyWith(color: b.dim),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
