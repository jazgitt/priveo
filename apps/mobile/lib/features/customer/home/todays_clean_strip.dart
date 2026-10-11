import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../support/feedback_sheet.dart';
import '../data/proof_reads_repository.dart';
import '../visit/visit_details_screen.dart';
import '../visit/visit_strings.dart';

/// The "Today's clean is done" strip on Home (HOME-03), with "View proof" and
/// "Rate today's clean" (HOME-05). It shows nothing until a visit of the
/// selected vehicle has been completed today.
class TodaysCleanStrip extends ConsumerWidget {
  const TodaysCleanStrip({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final clean = ref.watch(selectedTodayCleanProvider);
    if (clean == null) return const SizedBox.shrink();
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return SectionCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Symbols.check_circle_rounded, color: b.ok, fill: 1),
              const SizedBox(width: 10),
              Expanded(
                child: Text(VisitStrings.todayDone, style: text.titleSmall),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            VisitStrings.todaySummary(
              clean.finishedAt == null
                  ? ''
                  : VisitStrings.clock(clean.finishedAt!),
              clean.checksDone,
              clean.checksTotal,
              clean.photoCount,
            ),
            style: text.bodyMedium?.copyWith(color: b.mute),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: () => openVisitDetails(context, clean.visitId),
                  child: const Text(VisitStrings.viewProof),
                ),
              ),
              if (clean.rating == null) ...[
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () async {
                      await showVisitRatingSheet(context, clean.visitId);
                      ref.invalidate(todayCleansProvider);
                    },
                    child: const Text(VisitStrings.rateToday),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
