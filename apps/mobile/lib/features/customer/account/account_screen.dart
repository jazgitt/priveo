import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/auth/auth_controller.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../cust_strings.dart';
import '../data/customer_reads_repository.dart';
import '../history/history_screen.dart';
import '../notifications/notifications_screen.dart';
import '../settings/settings_screen.dart';
import '../vehicles/vehicles_screen.dart';

/// The account tab: who is signed in, links to the customer's lists, and
/// sign-out. It is a body; the customer shell supplies the scaffold.
class AccountScreen extends ConsumerWidget {
  const AccountScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final name = ref.watch(authControllerProvider).value?.displayName ?? '';
    final unread = ref.watch(inboxProvider).value?.unreadCount ?? 0;
    Widget link(
      IconData icon,
      String label,
      VoidCallback onTap, {
      String? badge,
    }) => Card(
      child: ListTile(
        leading: Icon(icon, color: b.gold),
        title: Text(label),
        trailing: badge == null
            ? const Icon(Symbols.chevron_right_rounded)
            : StatusChip(badge, tone: ChipTone.info),
        onTap: onTap,
      ),
    );
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 110),
      children: [
        Text(CustStrings.accountTitle, style: text.displaySmall),
        const SizedBox(height: 4),
        Text(name, style: text.bodyLarge?.copyWith(color: b.mute)),
        const SizedBox(height: 20),
        link(
          Symbols.directions_car_rounded,
          CustStrings.accountVehicles,
          () => openVehicles(context),
        ),
        link(
          Symbols.history_rounded,
          CustStrings.accountHistory,
          () => openHistory(context),
        ),
        link(
          Symbols.notifications_rounded,
          CustStrings.accountNotifications,
          () => openNotifications(context),
          badge: unread > 0 ? '$unread' : null,
        ),
        const SizedBox(height: 20),
        SectionLabel(CustStrings.settingsHeading),
        const SizedBox(height: 8),
        link(
          Symbols.tune_rounded,
          CustStrings.accountSettings,
          () => openSettings(context),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          icon: const Icon(Symbols.logout_rounded, size: 18),
          label: const Text(CustStrings.accountSignOut),
        ),
      ],
    );
  }
}
