import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/ui/theme.dart';
import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import '../customer/calendar/calendar_page.dart';
import '../customer/calendar/calendar_strings.dart';
import '../customer/home/home_schedule.dart' show ViewCalendarButton;
import '../customer/calendar/day_card.dart' show CallSupportButton;
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import 'schedule_refresh.dart';
import 'strings.dart';

/// Skip and un-skip a day (SKIP-01 to SKIP-08). Pausing is on its own screen
/// (`pause_screen.dart`). The 9 PM rule is checked by the API (SCHED-02); a
/// day past it shows the cutoff message and cannot be skipped.
class SkipPauseScreen extends ConsumerStatefulWidget {
  const SkipPauseScreen({super.key, required this.vehicleId});

  final String vehicleId;

  @override
  ConsumerState<SkipPauseScreen> createState() => _SkipPauseScreenState();
}

class _SkipPauseScreenState extends ConsumerState<SkipPauseScreen> {
  DateTime? _picked;
  bool _busy = false;
  String? _pickError;

  void _refresh() => refreshAfterScheduleChange(ref);

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirmSkip(List<UpcomingDayDto> days) async {
    final picked = _picked;
    if (picked == null) {
      setState(() => _pickError = MoneyStrings.skipPickFirst);
      return;
    }
    final day = days.firstWhere((d) => d.date == picked);
    if (!day.canChange) return; // Closed: the cutoff message explains.
    final repo = ref.read(moneyRepositoryProvider);
    await _run(() async {
      if (day.state == 'Skipped' && day.skipId != null) {
        await repo.unskip(widget.vehicleId, day.skipId!);
        if (mounted) {
          showMessage(context, MoneyStrings.unskipDone(formatDate(picked)));
        }
      } else {
        await repo.skip(widget.vehicleId, picked);
        if (mounted) {
          showMessage(context, MoneyStrings.skipDone(formatDate(picked)));
        }
      }
      _picked = null;
      _refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final upcoming = ref.watch(upcomingProvider(widget.vehicleId));
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.skipTitle)),
      body: upcoming.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(e), onRetry: _refresh),
        data: (days) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            ..._skipSection(days),
            const SizedBox(height: 24),
            ViewCalendarButton(onCalendar: () => openCalendarPage(context)),
          ],
        ),
      ),
    );
  }

  List<Widget> _skipSection(List<UpcomingDayDto> days) {
    final selected = _picked == null
        ? null
        : days.where((d) => d.date == _picked).firstOrNull;
    final undo = selected?.state == 'Skipped';
    // When tomorrow is already past the cutoff it starts selected, with the
    // cutoff message. Picking another day clears the message.
    final first = days.isEmpty ? null : days.first;
    final firstClosed =
        first != null && !first.canChange && first.state != 'Paused' ? first : null;
    final shown = selected ?? (_picked == null ? firstClosed : null);
    final closedShown =
        shown != null && !shown.canChange && shown.state != 'Paused' ? shown : null;
    return [
      SizedBox(
        height: 116,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: days.length,
          separatorBuilder: (_, _) => const SizedBox(width: 8),
          itemBuilder: (context, i) => _DayChip(
            day: days[i],
            selected: shown?.date == days[i].date,
            onTap: days[i].state == 'Paused'
                ? null
                : () => setState(() {
                      _picked = days[i].date;
                      _pickError = null;
                    }),
          ),
        ),
      ),
      if (_pickError != null)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(_pickError!,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
      const SizedBox(height: 16),
      PrimaryButton(
        label: undo ? MoneyStrings.undoSkip : MoneyStrings.skipConfirm,
        busy: _busy,
        onPressed: () => _confirmSkip(days),
      ),
      // After the 9 PM cutoff the controls close: point to support (SCHED-02).
      if (closedShown != null) ...[
        const SizedBox(height: 16),
        Text(CalStrings.closedMessageFor(formatDate(closedShown.date)),
            style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 8),
        const Align(
            alignment: Alignment.centerLeft, child: CallSupportButton()),
      ],
    ];
  }
}

class _DayChip extends StatelessWidget {
  const _DayChip({required this.day, required this.selected, required this.onTap});

  final UpcomingDayDto day;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final label = switch (day.state) {
      'Scheduled' => day.hasInterior ? 'Exterior + Interior' : 'Exterior',
      'Skipped' => MoneyStrings.skipped,
      'Completed' => MoneyStrings.completed,
      _ => MoneyStrings.paused,
    };
    // Text colour shows the status: Skipped yellow, Paused red, Completed green.
    final base = Theme.of(context).textTheme;
    final statusColor = switch (day.state) {
      'Skipped' => context.brand.warn,
      'Paused' => scheme.error,
      'Completed' => context.brand.ok,
      _ => null,
    };
    TextStyle? styled(TextStyle? s) => s?.copyWith(color: statusColor);
    return Semantics(
      button: true,
      selected: selected,
      enabled: onTap != null,
      label: '${DateFormat('EEEE d').format(day.date)}, $label'
          '${day.canChange ? '' : ', ${MoneyStrings.cutoffClosed}'}',
      child: ExcludeSemantics(
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Container(
            width: 96,
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                  color: selected ? scheme.primary : scheme.outlineVariant,
                  width: selected ? 2 : 1),
            ),
            child: Opacity(
              opacity: onTap == null || !day.canChange ? 0.5 : 1,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(DateFormat('EEE').format(day.date),
                      style: styled(base.labelMedium)),
                  Text(DateFormat('d').format(day.date),
                      style: styled(base.titleLarge)),
                  Flexible(
                    child: Text(label,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: styled(base.labelSmall)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
