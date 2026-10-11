import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../support/widgets.dart' show failureText;
import '../admin_quick_strings.dart';
import '../data/admin_quick_models.dart';
import '../data/admin_quick_providers.dart';

DateTime _dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

/// Jobs with no crew member (MQ-2, ADM-SCH-08). Read only.
class AdminNeedsSchedulingScreen extends ConsumerWidget {
  const AdminNeedsSchedulingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jobs = ref.watch(needsSchedulingProvider);
    return Scaffold(
      appBar: AppBar(title: Text(q('adminq_needs_title'))),
      body: jobs.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(context, e),
          onRetry: () => ref.invalidate(needsSchedulingProvider),
        ),
        data: (rows) => RefreshIndicator(
          onRefresh: () => ref.refresh(needsSchedulingProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (rows.isEmpty) Text(q('adminq_needs_empty')),
              for (final j in rows)
                Card(
                  child: ListTile(
                    title: Text('${j.service}, ${formatDate(j.date)}'),
                    subtitle: Text(
                      [
                        [
                          j.vehicle,
                          j.registration,
                        ].where((e) => e.isNotEmpty).join(', '),
                        if (j.reason.isNotEmpty) j.reason,
                      ].where((e) => e.isNotEmpty).join('\n'),
                    ),
                    isThreeLine: j.reason.isNotEmpty,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A society choice for the day and capacity screens. [allowAll] adds an
/// "All societies" entry whose value is the empty string.
class SocietyPicker extends StatelessWidget {
  const SocietyPicker({
    super.key,
    required this.societies,
    required this.value,
    required this.onChanged,
    this.allowAll = false,
  });

  final List<SocietyRef> societies;
  final String value;
  final ValueChanged<String> onChanged;
  final bool allowAll;

  @override
  Widget build(BuildContext context) => DropdownButtonFormField<String>(
    initialValue: value,
    decoration: InputDecoration(labelText: q('adminq_society')),
    items: [
      if (allowAll)
        DropdownMenuItem(value: '', child: Text(q('adminq_day_all_societies'))),
      for (final s in societies)
        DropdownMenuItem(value: s.id, child: Text(s.name)),
    ],
    onChanged: (v) => onChanged(v ?? ''),
  );
}

/// One date, jobs grouped by crew member. Read only (MQ-2, ADM-ACC-07 c).
class AdminDayScheduleScreen extends ConsumerStatefulWidget {
  const AdminDayScheduleScreen({super.key, this.initialDate});

  final DateTime? initialDate;

  @override
  ConsumerState<AdminDayScheduleScreen> createState() =>
      _AdminDayScheduleScreenState();
}

class _AdminDayScheduleScreenState
    extends ConsumerState<AdminDayScheduleScreen> {
  late DateTime _date = _dateOnly(widget.initialDate ?? DateTime.now());
  String _society = '';

  void _shift(int days) =>
      setState(() => _date = _date.add(Duration(days: days)));

  @override
  Widget build(BuildContext context) {
    final societies =
        ref.watch(adminQuickHomeProvider).value?.societies ?? const [];
    final day = ref.watch(
      dayScheduleProvider((date: _date, societyId: _society)),
    );
    return Scaffold(
      appBar: AppBar(title: Text(q('adminq_day_title'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SocietyPicker(
            societies: societies,
            value: _society,
            allowAll: true,
            onChanged: (v) => setState(() => _society = v),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              IconButton(
                tooltip: q('adminq_day_previous'),
                onPressed: () => _shift(-1),
                icon: const Icon(Icons.chevron_left),
              ),
              Expanded(
                child: Text(
                  formatDate(_date),
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              IconButton(
                tooltip: q('adminq_day_next'),
                onPressed: () => _shift(1),
                icon: const Icon(Icons.chevron_right),
              ),
            ],
          ),
          day.when(
            loading: () => const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => ErrorView(
              message: failureText(context, e),
              onRetry: () => ref.invalidate(dayScheduleProvider),
            ),
            data: (d) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  q('adminq_day_summary', {
                    'total': d.total,
                    'done': d.done,
                    'left': d.left,
                  }),
                ),
                if (d.scheduleStatus != null)
                  Text(q('adminq_day_status', {'status': d.scheduleStatus!})),
                const SizedBox(height: 8),
                if (d.total == 0) Text(q('adminq_day_empty')),
                for (final c in d.crew)
                  if (c.jobs.isNotEmpty || c.crewId != null)
                    SectionCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            c.crewName,
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          for (final j in c.jobs)
                            Padding(
                              padding: const EdgeInsets.only(top: 6),
                              child: Text(
                                '${j.time == null ? q('adminq_day_no_time') : formatClock(j.time!)}'
                                '  ${j.service}, ${[j.vehicle, j.registration].where((e) => e.isNotEmpty).join(' ')}'
                                ', ${j.status}${j.late ? ', ${q('adminq_day_late')}' : ''}',
                              ),
                            ),
                        ],
                      ),
                    ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Crew minutes against the work due for a week (MQ-2, ADM-CAP-01). Read only.
class AdminCapacityScreen extends ConsumerStatefulWidget {
  const AdminCapacityScreen({super.key, this.initialStart});

  final DateTime? initialStart;

  @override
  ConsumerState<AdminCapacityScreen> createState() =>
      _AdminCapacityScreenState();
}

class _AdminCapacityScreenState extends ConsumerState<AdminCapacityScreen> {
  late DateTime _start = _weekStart(widget.initialStart ?? DateTime.now());
  String? _society;

  /// A week starts on Sunday (ADM-SCH-09).
  static DateTime _weekStart(DateTime d) {
    final day = _dateOnly(d);
    return day.subtract(Duration(days: day.weekday % 7));
  }

  void _shift(int days) =>
      setState(() => _start = _start.add(Duration(days: days)));

  @override
  Widget build(BuildContext context) {
    final societies =
        ref.watch(adminQuickHomeProvider).value?.societies ?? const [];
    final society = _society ?? (societies.isEmpty ? '' : societies.first.id);
    final days = society.isEmpty
        ? null
        : ref.watch(capacityProvider((societyId: society, start: _start)));
    return Scaffold(
      appBar: AppBar(title: Text(q('adminq_capacity_title'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (societies.isNotEmpty)
            SocietyPicker(
              societies: societies,
              value: society,
              onChanged: (v) => setState(() => _society = v),
            ),
          const SizedBox(height: 8),
          Row(
            children: [
              IconButton(
                tooltip: q('adminq_capacity_previous'),
                onPressed: () => _shift(-7),
                icon: const Icon(Icons.chevron_left),
              ),
              Expanded(
                child: Text(
                  '${formatDate(_start)} - ${formatDate(_start.add(const Duration(days: 6)))}',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              IconButton(
                tooltip: q('adminq_capacity_next'),
                onPressed: () => _shift(7),
                icon: const Icon(Icons.chevron_right),
              ),
            ],
          ),
          if (days == null)
            Text(q('adminq_capacity_empty'))
          else
            days.when(
              loading: () => const Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => ErrorView(
                message: failureText(context, e),
                onRetry: () => ref.invalidate(capacityProvider),
              ),
              data: (rows) => Column(
                children: [
                  for (final d in rows)
                    Card(
                      child: ListTile(
                        title: Text(formatDate(d.date)),
                        subtitle: Text(
                          q('adminq_capacity_line', {
                            'capacity': d.capacityMinutes,
                            'demand': d.demandMinutes,
                            'scheduled': d.scheduledMinutes,
                          }),
                        ),
                        trailing: d.overCapacity
                            ? Text(
                                q('adminq_capacity_over'),
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.error,
                                ),
                              )
                            : null,
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
