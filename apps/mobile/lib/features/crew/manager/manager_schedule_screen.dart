import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/read_refresh.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';
import '../data/crew_repository.dart';
import 'manager_attendance_screen.dart';
import 'manager_hours_screen.dart';
import 'manager_job_screen.dart';

/// The whole society's schedule for a day, read-only, by crew member
/// (CRW-MGR-01). Attendance (CRW-MGR-04) and working hours (CRW-MGR-05) open
/// from the bar.
class ManagerScheduleScreen extends ConsumerStatefulWidget {
  const ManagerScheduleScreen({super.key});

  @override
  ConsumerState<ManagerScheduleScreen> createState() => _State();
}

class _State extends ConsumerState<ManagerScheduleScreen> {
  late DateTime _day = () {
    final n = DateTime.now();
    return DateTime(n.year, n.month, n.day);
  }();

  void _shift(int days) =>
      setState(() => _day = DateTime(_day.year, _day.month, _day.day + days));

  @override
  Widget build(BuildContext context) {
    final key = apiDate(_day);
    final schedule = ref.watch(managerScheduleProvider(key));
    return Scaffold(
      appBar: AppBar(
        title: Text(CrewText.team),
        actions: [
          IconButton(
            tooltip: CrewText.attendance,
            icon: const Icon(Symbols.event_available_rounded),
            onPressed: () async {
              await Navigator.of(context)
                  .push(crewRoute(const ManagerAttendanceScreen()));
              ref.invalidate(managerScheduleProvider(key));
            },
          ),
          IconButton(
            tooltip: CrewText.workingHours,
            icon: const Icon(Symbols.schedule_rounded),
            onPressed: () async {
              await Navigator.of(context)
                  .push(crewRoute(const ManagerHoursScreen()));
              ref.invalidate(managerScheduleProvider(key));
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Row(
            children: [
              IconButton(
                tooltip: CrewText.previousDay,
                icon: const Icon(Symbols.chevron_left_rounded),
                onPressed: () => _shift(-1),
              ),
              Expanded(
                child: Text(formatDate(_day),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.titleLarge),
              ),
              IconButton(
                tooltip: CrewText.nextDay,
                icon: const Icon(Symbols.chevron_right_rounded),
                onPressed: () => _shift(1),
              ),
            ],
          ),
          Expanded(
            child: schedule.when(
              skipLoadingOnReload: true,
              skipError: true,
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => ErrorView(
                message: failureText(e),
                onRetry: () => ref.invalidate(managerScheduleProvider(key)),
              ),
              data: (s) => RefreshIndicator(
                onRefresh: () => refreshAll(ref, () => ref.refresh(managerScheduleProvider(key).future)),
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    if (s.society.isNotEmpty) Text(s.society),
                    const SizedBox(height: 8),
                    for (final m in s.crew)
                      ExpansionTile(
                        key: ValueKey('crew-${m.id}'),
                        title: Text(m.name),
                        subtitle: Text(
                            '${m.role.isEmpty ? '' : '${m.role} · '}${CrewText.jobsCount(m.jobs.length)}'),
                        children: [
                          for (final job in m.jobs)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: JobCardTile(
                                  card: job, onTap: () => _open(job.id, key)),
                            ),
                        ],
                      ),
                    if (s.unassigned.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      SectionLabel(CrewText.unassigned),
                      const SizedBox(height: 8),
                      for (final job in s.unassigned)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: JobCardTile(
                              card: job, onTap: () => _open(job.id, key)),
                        ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _open(String jobId, String key) async {
    await Navigator.of(context).push(crewRoute(ManagerJobScreen(jobId: jobId)));
    ref.invalidate(managerScheduleProvider(key));
  }
}
