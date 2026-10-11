import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/util/format.dart';
import '../../changes_money/money_widgets.dart';
import 'calendar_actions.dart';
import 'calendar_strings.dart';
import 'day_card.dart' show pickCutoffTime;

const _weekdays = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

/// Edit the default cutoff time and the interior care day (SUB-08). Returns
/// true when something was saved.
Future<bool> showDefaultsSheet(
  BuildContext context, {
  required String vehicleId,
  String? cutoff,
  String? interiorDay,
}) async {
  final saved = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _DefaultsSheet(
      vehicleId: vehicleId,
      cutoff: cutoff,
      interiorDay: interiorDay,
    ),
  );
  return saved ?? false;
}

class _DefaultsSheet extends ConsumerStatefulWidget {
  const _DefaultsSheet({
    required this.vehicleId,
    required this.cutoff,
    required this.interiorDay,
  });

  final String vehicleId;
  final String? cutoff;
  final String? interiorDay;

  @override
  ConsumerState<_DefaultsSheet> createState() => _DefaultsSheetState();
}

class _DefaultsSheetState extends ConsumerState<_DefaultsSheet> {
  late String? _cutoff = widget.cutoff;
  late String? _day = widget.interiorDay;
  bool _busy = false;

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final r = await ref
          .read(calendarActionsProvider)
          .updatePreferences(
            widget.vehicleId,
            cutoffTime: _cutoff != widget.cutoff ? _cutoff : null,
            interiorDay: _day != widget.interiorDay ? _day : null,
          );
      if (!mounted) return;
      final extra = r.frozenDaysUnchanged > 0
          ? ' ${CalStrings.defaultsFrozen(r.frozenDaysUnchanged)}'
          : '';
      showMessage(
        context,
        '${CalStrings.defaultsSaved(formatDate(r.appliesFrom))}$extra',
      );
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        showFailure(context, e);
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final changed = _cutoff != widget.cutoff || _day != widget.interiorDay;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        4,
        20,
        20 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            CalStrings.defaultsTitle,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          OutlinedButton(
            onPressed: _busy
                ? null
                : () async {
                    final t = await pickCutoffTime(context, _cutoff);
                    if (t != null) setState(() => _cutoff = t);
                  },
            child: Text(
              _cutoff == null ? '--' : 'Cutoff time: ${formatClock(_cutoff!)}',
            ),
          ),
          if (widget.interiorDay != null) ...[
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _day,
              decoration: const InputDecoration(
                labelText: CalStrings.interiorDayLabel,
              ),
              items: [
                for (final d in _weekdays)
                  DropdownMenuItem(value: d, child: Text(d)),
              ],
              onChanged: _busy ? null : (v) => setState(() => _day = v),
            ),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy || !changed ? null : _save,
            child: const Text(CalStrings.save),
          ),
        ],
      ),
    );
  }
}
