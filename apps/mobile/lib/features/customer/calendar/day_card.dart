import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../changes_money/data/money_repository.dart';
import '../../changes_money/money_widgets.dart';
import '../../support/data/support_repository.dart';
import '../../support/widgets.dart' show linkOpenerProvider;
import '../cust_strings.dart';
import '../cust_ui.dart';
import '../data/customer_reads_repository.dart';
import '../visit/visit_details_screen.dart';
import 'calendar_actions.dart';
import 'calendar_strings.dart';

/// The card for the selected date (CAL-05 to CAL-10, SCHED-02).
class DayCard extends StatelessWidget {
  const DayCard({
    super.key,
    required this.date,
    required this.visits,
    required this.fallbackCutoff,
    required this.today,
    this.renewal,
  });

  final DateTime date;

  /// Today, date only.
  final DateTime today;
  final List<CalendarVisit> visits;

  /// The vehicle's default cutoff time, for a day that carries none.
  final String? fallbackCutoff;

  /// The renewal date, when it is this day.
  final DateTime? renewal;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return SectionCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(formatDate(date), style: text.titleMedium),
          const SizedBox(height: 10),
          if (visits.isEmpty)
            Row(
              children: [
                const StatusChip(CustStrings.noVisitChip),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    CustStrings.noVisit,
                    style: text.bodyMedium?.copyWith(color: b.mute),
                  ),
                ),
              ],
            ),
          for (final v in visits)
            DayVisitTile(
              visit: v,
              fallbackCutoff: fallbackCutoff,
              today: today,
            ),
          if (renewal != null) ...[
            const SizedBox(height: 8),
            Text(
              CalStrings.renews(formatDate(renewal!)),
              style: text.bodyMedium?.copyWith(color: b.mute),
            ),
          ],
        ],
      ),
    );
  }
}

class DayVisitTile extends ConsumerStatefulWidget {
  const DayVisitTile({
    super.key,
    required this.visit,
    required this.fallbackCutoff,
    required this.today,
  });

  final CalendarVisit visit;
  final String? fallbackCutoff;
  final DateTime today;

  @override
  ConsumerState<DayVisitTile> createState() => _DayVisitTileState();
}

class _DayVisitTileState extends ConsumerState<DayVisitTile> {
  bool _busy = false;

  CalendarVisit get v => widget.visit;

  String get _note {
    final cutoff = v.cutoffTime ?? widget.fallbackCutoff;
    if (v.changeRequested) {
      return v.requestedCutoffTime == null
          ? CalStrings.changeRequested
          : CalStrings.changeRequestedAt(formatClock(v.requestedCutoffTime!));
    }
    if (v.coveredOn != null) {
      return CalStrings.missedCovered(formatDate(v.coveredOn!));
    }
    if (v.rescheduledOn != null) {
      return CalStrings.missedRescheduled(formatDate(v.rescheduledOn!));
    }
    return switch (v.status) {
      'Completed' => CustStrings.viewDetails,
      'Skipped' => CustStrings.youSkipped,
      'Missed' => CustStrings.missedNote,
      'Paused' => CalStrings.pausedNote,
      'Projected' => CalStrings.expectedNote,
      _ =>
        cutoff == null
            ? CustStrings.proofAfterVisit
            : CustStrings.scheduledBy(formatClock(cutoff)),
    };
  }

  String get _chip => switch (v.status) {
    'Projected' => CalStrings.expectedChip,
    'Paused' => CalStrings.pausedChip,
    _ => v.status,
  };

  void _refresh() {
    ref.invalidate(calendarMonthProvider);
    ref.invalidate(nextServicesProvider);
    ref.invalidate(upcomingProvider);
    ref.invalidate(changesProvider);
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      _refresh();
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _skip() => _run(() async {
    await ref.read(calendarActionsProvider).skip(v.vehicleId, v.date);
    if (mounted) showMessage(context, CalStrings.skipDone(formatDate(v.date)));
  });

  Future<void> _unskip() => _run(() async {
    await ref.read(calendarActionsProvider).unskip(v.vehicleId, v.skipId!);
    if (mounted) {
      showMessage(context, CalStrings.unskipDone(formatDate(v.date)));
    }
  });

  Future<void> _cutoff() async {
    final current = v.cutoffTime ?? widget.fallbackCutoff;
    final picked = await pickCutoffTime(context, current);
    if (picked == null) return;
    await _run(() async {
      final r = await ref
          .read(calendarActionsProvider)
          .changeCutoff(v.vehicleId, v.date, picked);
      if (mounted) {
        showMessage(
          context,
          r.requested
              ? CalStrings.cutoffRequested
              : CalStrings.cutoffApplied(
                  formatDate(v.date),
                  formatClock(picked),
                ),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final open = v.status == 'Completed' && v.visitId != null;
    final upcoming = const ['Scheduled', 'Projected'].contains(v.status);
    final canSkipOrCutoff = v.canChange && upcoming;
    final canUndo = v.canChange && v.status == 'Skipped' && v.skipId != null;
    // After the 9 PM cutoff the controls close and the customer is pointed to
    // support (SCHED-02).
    final closed =
        !v.canChange &&
        !v.date.isBefore(widget.today) &&
        const ['Scheduled', 'Projected', 'Skipped'].contains(v.status);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: open ? () => openVisitDetails(context, v.visitId!) : null,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        v.services.isEmpty ? '' : v.services.join(' + '),
                        style: text.titleSmall,
                      ),
                    ),
                    StatusChip(
                      _chip,
                      tone: v.status == 'Projected'
                          ? ChipTone.neutral
                          : statusTone(v.status),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(_note, style: text.bodyMedium?.copyWith(color: b.mute)),
              ],
            ),
          ),
          if (v.crewName != null && v.startTime != null) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(Symbols.person_rounded, size: 16, color: b.mute),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    CalStrings.crewAt(
                      v.crewName!,
                      formatClock(v.startTime!),
                      formatClock(v.endTime ?? v.startTime!),
                    ),
                    style: text.bodyMedium?.copyWith(color: b.mute),
                  ),
                ),
              ],
            ),
          ],
          if (canSkipOrCutoff || canUndo) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              children: [
                if (canSkipOrCutoff)
                  OutlinedButton(
                    onPressed: _busy ? null : _skip,
                    child: const Text(CalStrings.skipDate),
                  ),
                if (canSkipOrCutoff)
                  OutlinedButton(
                    onPressed: _busy ? null : _cutoff,
                    child: const Text(CalStrings.changeCutoff),
                  ),
                if (canUndo)
                  OutlinedButton(
                    onPressed: _busy ? null : _unskip,
                    child: const Text(CalStrings.undoSkip),
                  ),
              ],
            ),
          ],
          if (closed) ...[
            const SizedBox(height: 10),
            Text(
              CalStrings.closedMessage,
              style: text.bodyMedium?.copyWith(color: b.mute),
            ),
            const SizedBox(height: 8),
            const CallSupportButton(),
          ],
        ],
      ),
    );
  }
}

/// "Call support": opens the helpline number in the phone (SCHED-02, SUP-02).
class CallSupportButton extends ConsumerWidget {
  const CallSupportButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return OutlinedButton.icon(
      icon: const Icon(Symbols.call_rounded, size: 18),
      label: const Text(CalStrings.callSupport),
      onPressed: () async {
        final messenger = ScaffoldMessenger.of(context);
        var ok = false;
        try {
          final c = await ref.read(supportContactProvider.future);
          ok = await ref.read(linkOpenerProvider)(
            Uri(scheme: 'tel', path: c.helpline),
          );
        } catch (_) {
          ok = false;
        }
        if (!ok) {
          messenger.showSnackBar(
            const SnackBar(content: Text(CalStrings.cannotOpenPhone)),
          );
        }
      },
    );
  }
}

/// A list of times in 30-minute steps. Returns the chosen `HH:MM`, or null.
Future<String?> pickCutoffTime(BuildContext context, String? current) {
  const rowHeight = 56.0;
  final times = halfHourSteps();
  final start = times.indexOf(current ?? '06:00').clamp(0, times.length - 1);
  return showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    builder: (context) => SafeArea(
      child: ListView(
        controller: ScrollController(initialScrollOffset: start * rowHeight),
        itemExtent: rowHeight,
        children: [
          for (final t in times)
            ListTile(
              title: Text(formatClock(t)),
              selected: t == current,
              trailing: t == current ? const Icon(Symbols.check_rounded) : null,
              onTap: () => Navigator.of(context).pop(t),
            ),
        ],
      ),
    ),
  );
}
