import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import '../customer/calendar/calendar_strings.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import 'schedule_refresh.dart';
import 'strings.dart';

/// Pause the service for a range of dates, and end a pause (PAUSE-01 to
/// PAUSE-07). It has only the pause feature; skipping a day is on its own
/// screen. It opens from My subscription.
class PauseScreen extends ConsumerStatefulWidget {
  const PauseScreen({super.key, required this.vehicleId});

  final String vehicleId;

  @override
  ConsumerState<PauseScreen> createState() => _PauseScreenState();
}

class _PauseScreenState extends ConsumerState<PauseScreen> {
  DateTime? _from;
  DateTime? _to;
  bool _busy = false;
  String? _pauseError;
  String? _pauseResult;

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

  /// The visits paused and the new renewal date, before confirming
  /// (PAUSE-02). One visit a day, and the renewal moves a day for each.
  String _pausePreview(DateTime? renewal) {
    final n = _to!.difference(_from!).inDays + 1;
    final moved = renewal?.add(Duration(days: n));
    return CalStrings.pausePreview(
        n, renewal == null ? null : formatDate(renewal), moved == null ? null : formatDate(moved));
  }

  @override
  Widget build(BuildContext context) {
    final changes = ref.watch(changesProvider(widget.vehicleId)).value;
    String show(DateTime? d) => d == null ? '--' : formatDate(d);
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.pauseService)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
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
          if (_from != null && _to != null && _pauseResult == null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_pausePreview(changes?.renewalDate)),
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
        ],
      ),
    );
  }
}
