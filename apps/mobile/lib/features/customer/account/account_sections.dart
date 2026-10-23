import '../../../core/features/feature_flags.dart';
import '../../../core/features/feature_keys.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/auth/auth_controller.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../changes_money/routes.dart' as money;
import '../../support/routes.dart';
import '../calendar/calendar_page.dart';
import '../data/customer_reads_repository.dart';
import 'account_data.dart';
import 'account_strings.dart';
import 'profile_screens.dart';

/// The top of Account (ACC-01): initials, full name and mobile number. Tapping
/// it opens Edit profile (ACC-06). Until the profile loads it shows the name
/// from the sign-in.
class AccountProfileHeader extends ConsumerWidget {
  const AccountProfileHeader({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final profile = ref.watch(profileProvider).value;
    final name =
        profile?.fullName ??
        ref.watch(authControllerProvider).value?.displayName ??
        '';
    final initials = profile?.initials ?? (name.isEmpty ? '' : name[0]);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => openEditProfile(context),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: b.gold.withValues(alpha: 0.18),
                child: Text(
                  initials.toUpperCase(),
                  style: text.titleMedium?.copyWith(color: b.goldHi),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: text.titleMedium),
                    if (profile != null)
                      Text(
                        profile.mobile,
                        style: text.bodyMedium?.copyWith(color: b.mute),
                      ),
                    if (profile?.memberSince != null)
                      Text(
                        '${AccountStrings.memberSince} '
                        '${formatDate(profile!.memberSince!)}',
                        style: text.bodySmall?.copyWith(color: b.mute),
                      ),
                  ],
                ),
              ),
              const Icon(Symbols.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}

/// One subscription card for each vehicle (ACC-02). It opens that vehicle's
/// My subscription. A vehicle with no subscription gets no card.
class AccountSubscriptionCards extends ConsumerWidget {
  const AccountSubscriptionCards({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final vehicles = ref.watch(accountVehiclesProvider).value ?? const [];
    final subscribed = [
      for (final v in vehicles)
        if (v.subscriptionStatus != null) v,
    ];
    if (subscribed.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        const SectionLabel(AccountStrings.subscriptions),
        const SizedBox(height: 8),
        for (final v in subscribed) _SubscriptionCard(v),
      ],
    );
  }
}

class _SubscriptionCard extends ConsumerWidget {
  const _SubscriptionCard(this.vehicle);

  final VehicleSummaryDto vehicle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final sub = ref.watch(accountSubscriptionProvider(vehicle.id)).value;
    final status = sub?.status ?? vehicle.subscriptionStatus!;
    final car = vehicle.registration.isEmpty
        ? vehicle.model
        : '${vehicle.model} · ${vehicle.registration}';
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: ref.watch(featureOnProvider(FeatureKeys.subscription))
            ? () => context.push(money.subscriptionPath(vehicle.id))
            : null,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: Text(car, style: text.titleSmall)),
                  StatusChip(status, tone: StatusChip.toneFor(status)),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                [
                  if (sub?.planName != null) sub!.planName!,
                  vehicle.society,
                ].join(' · '),
                style: text.bodySmall?.copyWith(color: b.mute),
              ),
              if (sub != null) ...[
                const SizedBox(height: 8),
                Text(
                  '${AccountStrings.expires} ${formatDate(sub.endDate)}'
                  ' · ${formatRupees(sub.monthlyPriceRupees)} '
                  '${AccountStrings.perMonth}',
                  style: text.bodyMedium,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// The vehicle a menu action is for: the only one, or the customer's choice.
Future<String?> _chooseVehicle(BuildContext context, WidgetRef ref) async {
  final vehicles = await ref.read(accountVehiclesProvider.future);
  if (vehicles.isEmpty || !context.mounted) return null;
  if (vehicles.length == 1) return vehicles.first.id;
  return showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    builder: (sheet) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const ListTile(title: Text(AccountStrings.chooseVehicle)),
          for (final v in vehicles)
            ListTile(
              leading: const Icon(Symbols.directions_car_rounded),
              title: Text(v.model),
              subtitle: v.registration.isEmpty ? null : Text(v.registration),
              onTap: () => Navigator.of(sheet).pop(v.id),
            ),
        ],
      ),
    ),
  );
}

/// The menu rows ACC-03 adds to Account: calendar, add-ons, skip or pause,
/// complaints, help and support, and change password.
class AccountMoreLinks extends ConsumerWidget {
  const AccountMoreLinks({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final b = context.brand;
    Widget link(IconData icon, String label, VoidCallback onTap) => Card(
      child: ListTile(
        leading: Icon(icon, color: b.gold),
        title: Text(label),
        trailing: const Icon(Symbols.chevron_right_rounded),
        onTap: onTap,
      ),
    );
    Future<void> forVehicle(String Function(String id) path) async {
      final id = await _chooseVehicle(context, ref);
      if (id != null && context.mounted) context.push(path(id));
    }

    bool on(String key) => ref.watch(featureOnProvider(key));
    return Column(
      children: [
        link(
          Symbols.calendar_month_rounded,
          AccountStrings.menuCalendar,
          () => openCalendarPage(context),
        ),
        if (on(FeatureKeys.addons))
          link(
            Symbols.auto_awesome_rounded,
            AccountStrings.menuAddons,
            () => forVehicle(money.addonsPath),
          ),
        if (on(FeatureKeys.skipPause))
          link(
            Symbols.pause_circle_rounded,
            AccountStrings.menuSkipPause,
            () => forVehicle(money.skipPausePath),
          ),
        if (on(FeatureKeys.complaints))
          link(
            Symbols.report_rounded,
            AccountStrings.menuComplaints,
            () => context.push(SupportRoutes.complaints),
          ),
        if (on(FeatureKeys.help))
          link(
            Symbols.help_rounded,
            AccountStrings.menuHelp,
            () => context.push(SupportRoutes.help),
          ),
        link(
          Symbols.lock_rounded,
          AccountStrings.changePassword,
          () => openChangePassword(context),
        ),
      ],
    );
  }
}
