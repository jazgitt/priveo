import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../cust_strings.dart';
import '../cust_ui.dart';
import '../data/customer_reads_repository.dart';

/// Opens My vehicles over the current screen.
void openVehicles(BuildContext context) {
  Navigator.of(
    context,
  ).push(MaterialPageRoute<void>(builder: (_) => const VehiclesScreen()));
}

/// My vehicles (VEH-06): registration, make and model, and the subscription
/// status of each. Tapping one opens its details.
class VehiclesScreen extends ConsumerWidget {
  const VehiclesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return CustPage(
      title: CustStrings.vehiclesTitle,
      body: AsyncBody<List<VehicleSummaryDto>>(
        value: ref.watch(vehiclesProvider),
        onRetry: () => ref.invalidate(vehiclesProvider),
        builder: (vehicles) {
          if (vehicles.isEmpty) {
            return Center(child: Text(CustStrings.vehiclesEmpty));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: vehicles.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, i) {
              final v = vehicles[i];
              final status = v.subscriptionStatus;
              return Card(
                child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => VehicleDetailScreen(vehicleId: v.id),
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                v.registration.isEmpty
                                    ? CustStrings.numberToBeAdded
                                    : v.registration,
                                style: text.titleSmall,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                v.model,
                                style: text.bodyMedium?.copyWith(color: b.mute),
                              ),
                            ],
                          ),
                        ),
                        StatusChip(
                          status ?? CustStrings.noSubscription,
                          tone: status == null
                              ? ChipTone.neutral
                              : statusTone(status),
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
    );
  }
}

/// One vehicle's details (VEH-02, VEH-03). Editing is not in this slice.
class VehicleDetailScreen extends ConsumerWidget {
  const VehicleDetailScreen({super.key, required this.vehicleId});

  final String vehicleId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    Widget row(String label, String? value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 4,
            child: Text(label, style: text.bodyMedium?.copyWith(color: b.mute)),
          ),
          Expanded(
            flex: 5,
            child: Text(
              value == null || value.isEmpty ? CustStrings.notOnFile : value,
              style: text.bodyMedium,
            ),
          ),
        ],
      ),
    );
    return CustPage(
      title: CustStrings.vehicleTitle,
      body: AsyncBody<VehicleDetailDto>(
        value: ref.watch(vehicleDetailProvider(vehicleId)),
        onRetry: () => ref.invalidate(vehicleDetailProvider(vehicleId)),
        builder: (v) {
          final price = v.monthlyPriceRupees;
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              SectionCard(
                child: Column(
                  children: [
                    row(CustStrings.fieldRegistration, v.registration),
                    row(
                      CustStrings.fieldCar,
                      [v.make, v.model].where((s) => s.isNotEmpty).join(' '),
                    ),
                    row(CustStrings.fieldVariant, v.variant),
                    row(CustStrings.fieldCategory, v.category),
                    row(CustStrings.fieldSociety, v.society),
                    row(CustStrings.fieldParking, v.parking),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SectionCard(
                child: Column(
                  children: [
                    row(
                      CustStrings.fieldPlan,
                      price == null ? null : '${formatRupees(price)} a month',
                    ),
                    row(
                      CustStrings.fieldCutoff,
                      v.cutoffTime == null ? null : formatClock(v.cutoffTime!),
                    ),
                    row(CustStrings.fieldInteriorDay, v.interiorDay),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Text(
                CustStrings.carDetailsViaSupport,
                style: text.bodySmall?.copyWith(color: b.mute),
              ),
            ],
          );
        },
      ),
    );
  }
}
