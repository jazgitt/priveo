import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';
import '../data/manager_models.dart';

/// The society's crew with their working hours (CRW-MGR-05). A Manager can
/// change hours, not roles, societies or passwords.
class ManagerHoursScreen extends ConsumerWidget {
  const ManagerHoursScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hours = ref.watch(managerHoursProvider);
    return Scaffold(
      appBar: AppBar(title: Text(CrewText.workingHours)),
      body: hours.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(managerHoursProvider),
        ),
        data: (list) => list.isEmpty
            ? Center(child: Text(CrewText.noCrew))
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final c in list)
                    Card(
                      child: ListTile(
                        key: ValueKey('hours-${c.crewId}'),
                        title: Text(c.name),
                        subtitle: Text(c.role),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () async {
                          await Navigator.of(context)
                              .push(crewRoute(ManagerHoursEditScreen(hours: c)));
                          ref.invalidate(managerHoursProvider);
                        },
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}

/// One crew member's seven days: working or not, and the start and end.
class ManagerHoursEditScreen extends ConsumerStatefulWidget {
  const ManagerHoursEditScreen({super.key, required this.hours});

  final CrewHours hours;

  @override
  ConsumerState<ManagerHoursEditScreen> createState() => _EditState();
}

class _EditState extends ConsumerState<ManagerHoursEditScreen> {
  late final List<HoursDay> _days = List.of(widget.hours.days);
  bool _busy = false;

  void _set(int i, HoursDay d) => setState(() => _days[i] = d);

  Future<void> _pick(int i, {required bool start}) async {
    final day = _days[i];
    final current = (start ? day.start : day.end).split(':');
    final picked = await showTimePicker(
      context: context,
      helpText: start ? CrewText.startTime : CrewText.endTime,
      initialTime: current.length == 2
          ? TimeOfDay(
              hour: int.tryParse(current[0]) ?? 6,
              minute: int.tryParse(current[1]) ?? 0)
          : TimeOfDay(hour: start ? 6 : 11, minute: 0),
    );
    if (picked == null) return;
    final text = '${picked.hour.toString().padLeft(2, '0')}:'
        '${picked.minute.toString().padLeft(2, '0')}';
    _set(i, start ? day.copyWith(start: text) : day.copyWith(end: text));
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final result = await ref
          .read(crewRepositoryProvider)
          .managerSetHours(widget.hours.crewId, _days);
      ref.invalidate(managerHoursProvider);
      if (!mounted) return;
      final moved = result.released.where((j) => j.reassigned).length;
      final waiting = result.released.length - moved;
      showSnack(
          context,
          result.released.isEmpty
              ? CrewText.hoursSaved
              : '${CrewText.hoursSaved} ${CrewText.releasedJobs(moved, waiting)}');
      Navigator.of(context).pop();
    } catch (e) {
      if (mounted) showSnack(context, failureText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.hours.name)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (var i = 0; i < _days.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                key: ValueKey('hours-day-${_days[i].day}'),
                children: [
                  Expanded(
                    flex: 3,
                    child: SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(_days[i].day),
                      subtitle: Text(
                          _days[i].working ? CrewText.working : CrewText.dayOff),
                      value: _days[i].working,
                      onChanged: (v) => _set(
                          i,
                          _days[i].copyWith(
                            working: v,
                            start: v && _days[i].start.isEmpty
                                ? '06:00'
                                : _days[i].start,
                            end: v && _days[i].end.isEmpty
                                ? '11:00'
                                : _days[i].end,
                          )),
                    ),
                  ),
                  if (_days[i].working) ...[
                    TextButton(
                      onPressed: () => _pick(i, start: true),
                      child: Text(_days[i].start),
                    ),
                    const Text('-'),
                    TextButton(
                      onPressed: () => _pick(i, start: false),
                      child: Text(_days[i].end),
                    ),
                  ],
                ],
              ),
            ),
          const SizedBox(height: 16),
          PrimaryButton(label: CrewText.save, busy: _busy, onPressed: _save),
        ],
      ),
    );
  }
}
