import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../cust_strings.dart';
import '../cust_ui.dart';
import '../data/customer_reads_repository.dart';
import '../home/customer_home_data.dart';
import '../visit/visit_details_screen.dart';

/// Opens the service history over the current screen.
void openHistory(BuildContext context) {
  Navigator.of(
    context,
  ).push(MaterialPageRoute<void>(builder: (_) => const HistoryScreen()));
}

/// Visits that are over, newest first, for the selected vehicle (SVC-09).
class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final home = ref.watch(customerHomeProvider).value;
    String? vehicleId;
    if (home != null && home.vehicles.isNotEmpty) {
      vehicleId = home
          .vehicles[selectedIndex(
            home.vehicles,
            ref.watch(selectedVehicleProvider),
          )]
          .id;
    }
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return CustPage(
      title: CustStrings.historyTitle,
      body: AsyncBody<List<HistoryItemDto>>(
        value: ref.watch(historyProvider(vehicleId)),
        onRetry: () => ref.invalidate(historyProvider(vehicleId)),
        builder: (items) {
          if (items.isEmpty) {
            return Center(child: Text(CustStrings.historyEmpty));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, i) {
              final h = items[i];
              final completed = h.status == 'Completed';
              return Card(
                child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: completed
                      ? () => openVisitDetails(context, h.visitId)
                      : null,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(formatDate(h.date), style: text.titleSmall),
                              const SizedBox(height: 4),
                              Text(
                                [
                                  h.services.join(' + '),
                                  if (h.photoCount > 0)
                                    CustStrings.photoCount(h.photoCount),
                                ].where((s) => s.isNotEmpty).join('  ·  '),
                                style: text.bodySmall?.copyWith(color: b.mute),
                              ),
                            ],
                          ),
                        ),
                        StatusChip(h.status, tone: statusTone(h.status)),
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
