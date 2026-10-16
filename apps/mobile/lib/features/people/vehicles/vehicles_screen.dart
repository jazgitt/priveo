import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/read_refresh.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/api/api.g.dart' show VehicleCard;
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../customer/home/customer_home_data.dart';
import '../people_strings.dart';

/// "My vehicles" (VEH-06): every vehicle with its registration, model and
/// subscription status. Tapping one opens its details.
class VehiclesScreen extends ConsumerWidget {
  const VehiclesScreen({super.key});

  static const _s = PeopleStrings.instance;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final home = ref.watch(customerHomeProvider);
    return Scaffold(
      appBar: AppBar(title: Text(_s.vehiclesTitle)),
      body: home.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            ErrorView(onRetry: () => ref.invalidate(customerHomeProvider)),
        data: (h) => h.vehicles.isEmpty
            ? Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(l.noVehicles, textAlign: TextAlign.center),
                ),
              )
            : RefreshIndicator(
                onRefresh: () => refreshAll(ref, () => ref.read(customerHomeProvider.future)),
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    for (final v in h.vehicles) ...[
                      _VehicleTile(v),
                      const SizedBox(height: 12),
                    ],
                  ],
                ),
              ),
      ),
    );
  }
}

class _VehicleTile extends StatelessWidget {
  const _VehicleTile(this.vehicle);

  final VehicleCard vehicle;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Semantics(
      button: true,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => context.push('/customer/vehicles/${vehicle.id}'),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 56),
          child: SectionCard(
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        vehicle.registration.isEmpty
                            ? l.noRegistration
                            : vehicle.registration,
                        style: theme.textTheme.titleMedium,
                      ),
                      const SizedBox(height: 2),
                      Text(vehicle.model),
                      if ((vehicle.planName ?? '').isNotEmpty)
                        Text(vehicle.planName!, style: theme.textTheme.bodySmall),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                StatusChip(
                  vehicle.subscriptionStatus ?? l.noSubscription,
                  tone: vehicle.subscriptionStatus == null
                      ? ChipTone.neutral
                      : StatusChip.toneFor(vehicle.subscriptionStatus!),
                ),
                const SizedBox(width: 4),
                const ExcludeSemantics(
                    child: Icon(Symbols.chevron_right_rounded)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// One vehicle's details (VEH-02, VEH-03) and its subscription summary
/// (SUB-02). Car details change only through support (VEH-04), so nothing
/// here is editable.
class VehicleDetailScreen extends ConsumerWidget {
  const VehicleDetailScreen({super.key, required this.vehicleId});

  final String vehicleId;

  static const _s = PeopleStrings.instance;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final home = ref.watch(customerHomeProvider);
    return Scaffold(
      appBar: AppBar(title: Text(_s.vehicleDetails)),
      body: home.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            ErrorView(onRetry: () => ref.invalidate(customerHomeProvider)),
        data: (h) {
          final matches = h.vehicles.where((v) => v.id == vehicleId);
          if (matches.isEmpty) {
            return ErrorView(
              message: _s.vehicleNotFound,
              onRetry: () => ref.invalidate(customerHomeProvider),
            );
          }
          final v = matches.first;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              SectionCard(
                child: Column(
                  children: [
                    _Row(l.registration,
                        v.registration.isEmpty ? l.noRegistration : v.registration),
                    _Row(l.vehicle, v.model),
                    _Row(l.society, v.society),
                    _Row(l.parking,
                        v.parking.isEmpty ? l.noParking : v.parking),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SectionLabel(l.subscription),
              const SizedBox(height: 8),
              SectionCard(
                child: v.subscriptionStatus == null
                    ? Text(l.noSubscription)
                    : Column(
                        children: [
                          _Row(_s.subscriptionStatus, v.subscriptionStatus!),
                          if ((v.planName ?? '').isNotEmpty) _Row(_s.plan, v.planName!),
                          if (v.expiresOn != null)
                            _Row(_s.expiresOn, formatDate(v.expiresOn!)),
                          if (v.monthlyPriceRupees != null)
                            _Row(_s.monthlyAmount,
                                formatRupees(v.monthlyPriceRupees!)),
                          if (v.cutoffTime != null)
                            _Row(l.cutoffTime, formatClock(v.cutoffTime!)),
                          if (v.interiorDay != null)
                            _Row(l.interiorCareDay, v.interiorDay!),
                        ],
                      ),
              ),
              const SizedBox(height: 16),
              Text(
                l.onlyPriveoCanChange,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Theme.of(context).hintColor),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: TextStyle(color: Theme.of(context).hintColor)),
            const SizedBox(width: 16),
            Flexible(child: Text(value, textAlign: TextAlign.end)),
          ],
        ),
      );
}
