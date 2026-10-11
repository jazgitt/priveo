import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import 'strings.dart';

/// Skip, un-skip, pause and end a pause (SKIP-01 to SKIP-08, PAUSE-01 to
/// PAUSE-07). The 9 PM rule is checked by the API; the chips for dates past
/// it are disabled (SCHED-02).
class SkipPauseScreen extends ConsumerStatefulWidget {
  const SkipPauseScreen({super.key, required this.vehicleId});

  final String vehicleId;

  @override
  ConsumerState<SkipPauseScreen> createState() => _SkipPauseScreenState();
}

class _SkipPauseScreenState extends ConsumerState<SkipPauseScreen> {
  bool _pauseTab = false;
  DateTime? _picked;
  DateTime? _from;
  DateTime? _to;
  bool _busy = false;
  String? _pickError;
  String? _pauseError;
  String? _pauseResult;

  void _refresh() {
    ref.invalidate(upcomingProvider(widget.vehicleId));
    ref.invalidate(changesProvider(widget.vehicleId));
  }

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

  Future<void> _pickDate(bool from) async {
    final now = DateTime.now();
    final first = DateTime(now.year, now.month, now.day).add(const Duration(days: 1));
    final chosen = await showDatePicker(
      context: context,
      initialDate: (from ? _from : _to) ?? _from ?? first,
      firstDate: from ? first : (_from ?? first),
      lastDate: first.add(const Duration(days: 365)),
    );
    if (chosen == null) return;
    setState(() {
      if (from) {
        _from = chosen;
        if (_to != null && _to!.isBefore(chosen)) _to = chosen;
      } else {
        _to = chosen;
      }
      _pauseError = null;
      _pauseResult = null;
    });
  }

  Future<void> _confirmPause() async {
    if (_from == null || _to == null) {
      setState(() => _pauseError = MoneyStrings.pauseChoose);
      return;
    }
    await _run(() async {
      final p = await ref
          .read(moneyRepositoryProvider)
          .pause(widget.vehicleId, _from!, _to!);
      _pauseResult = MoneyStrings.pauseDone(
          formatDate(p.startDate),
          formatDate(p.endDate),
          p.renewalDate == null ? '' : formatDate(p.renewalDate!));
      _from = null;
      _to = null;
      _refresh();
    });
  }

  Future<void> _endPause(ChangeDto pause) => _run(() async {
        await ref.read(moneyRepositoryProvider).endPause(widget.vehicleId, pause.id);
        if (mounted) showMessage(context, MoneyStrings.pauseEnded);
        _refresh();
      });

  @override
  Widget build(BuildContext context) {
    final upcoming = ref.watch(upcomingProvider(widget.vehicleId));
    final changes = ref.watch(changesProvider(widget.vehicleId));
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.skipTitle)),
      body: upcoming.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(e), onRetry: _refresh),
        data: (days) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text(MoneyStrings.skipTab)),
                ButtonSegment(value: true, label: Text(MoneyStrings.pauseTab)),
              ],
              selected: {_pauseTab},
              onSelectionChanged: (s) => setState(() => _pauseTab = s.first),
            ),
            const SizedBox(height: 16),
            if (!_pauseTab) ..._skipSection(days) else ..._pauseSection(changes.value),
            const SizedBox(height: 24),
            const SectionLabel(MoneyStrings.upcoming),
            const SizedBox(height: 8),
            for (final d in days.take(7)) _UpcomingRow(d),
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
    return [
      const Text(MoneyStrings.skipInstruction),
      const SizedBox(height: 12),
      SizedBox(
        height: 116,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: days.length,
          separatorBuilder: (_, _) => const SizedBox(width: 8),
          itemBuilder: (context, i) => _DayChip(
            day: days[i],
            selected: _picked == days[i].date,
            onTap: days[i].state == 'Paused' || !days[i].canChange
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
      if (selected != null && !undo)
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Text(MoneyStrings.skipNote(formatDate(selected.date))),
        ),
      const SizedBox(height: 16),
      PrimaryButton(
        label: undo ? MoneyStrings.undoSkip : MoneyStrings.skipConfirm,
        busy: _busy,
        onPressed: () => _confirmSkip(days),
      ),
    ];
  }

  List<Widget> _pauseSection(ChangesDto? changes) {
    String show(DateTime? d) => d == null ? '--' : formatDate(d);
    return [
      Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: () => _pickDate(true),
              child: Text('${MoneyStrings.pauseFrom}: ${show(_from)}'),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: OutlinedButton(
              onPressed: () => _pickDate(false),
              child: Text('${MoneyStrings.pauseTo}: ${show(_to)}'),
            ),
          ),
        ],
      ),
      if (_pauseError != null)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(_pauseError!,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
      if (_pauseResult != null)
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Text(_pauseResult!),
        ),
      const SizedBox(height: 16),
      PrimaryButton(
          label: MoneyStrings.pauseConfirm, busy: _busy, onPressed: _confirmPause),
      if (changes != null && changes.pauses.isNotEmpty) ...[
        const SizedBox(height: 24),
        const SectionLabel(MoneyStrings.yourPauses),
        for (final p in changes.pauses)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(MoneyStrings.pausePeriod(
                formatDate(p.startDate), formatDate(p.endDate))),
            trailing: TextButton(
              onPressed: _busy ? null : () => _endPause(p),
              child: const Text(MoneyStrings.endPause),
            ),
          ),
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
    final label = day.state == 'Scheduled'
        ? (day.hasInterior ? 'Exterior + Interior' : 'Exterior')
        : (day.state == 'Skipped' ? MoneyStrings.skipped : MoneyStrings.paused);
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
              opacity: onTap == null ? 0.5 : 1,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(DateFormat('EEE').format(day.date),
                      style: Theme.of(context).textTheme.labelMedium),
                  Text(DateFormat('d').format(day.date),
                      style: Theme.of(context).textTheme.titleLarge),
                  Flexible(
                    child: Text(label,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.labelSmall),
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

class _UpcomingRow extends StatelessWidget {
  const _UpcomingRow(this.day);

  final UpcomingDayDto day;

  @override
  Widget build(BuildContext context) {
    final type = day.hasInterior ? 'Exterior + Interior' : 'Exterior';
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text('${DateFormat('EEE').format(day.date)} ${formatDate(day.date)}'),
      subtitle: Text(type),
      trailing: day.state == 'Scheduled'
          ? null
          : StatusChip(day.state == 'Skipped' ? MoneyStrings.skipped : MoneyStrings.paused,
              tone: ChipTone.neutral),
    );
  }
}
