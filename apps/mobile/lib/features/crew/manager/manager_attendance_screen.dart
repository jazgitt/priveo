import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';
import '../data/crew_repository.dart';
import '../data/manager_models.dart';

String _statusLabel(AttendanceEntry e) => switch (e.status) {
      Attendance.sick => CrewText.attendanceSick,
      Attendance.leave => CrewText.attendanceLeave,
      Attendance.lateStart => e.lateStart.isEmpty
          ? CrewText.attendanceLateStart
          : CrewText.lateStartAt(e.lateStart),
      _ => CrewText.attendancePresent,
    };

String _optionLabel(String status) => switch (status) {
      Attendance.sick => CrewText.attendanceSick,
      Attendance.leave => CrewText.attendanceLeave,
      Attendance.lateStart => CrewText.attendanceLateStart,
      _ => CrewText.attendancePresent,
    };

/// Who is in, away or starting late, for a day of the Manager's society
/// (CRW-MGR-04). A change moves the crew member's open jobs at once.
class ManagerAttendanceScreen extends ConsumerStatefulWidget {
  const ManagerAttendanceScreen({super.key});

  @override
  ConsumerState<ManagerAttendanceScreen> createState() => _State();
}

class _State extends ConsumerState<ManagerAttendanceScreen> {
  late final DateTime _today = () {
    final n = DateTime.now();
    return DateTime(n.year, n.month, n.day);
  }();
  late DateTime _day = _today;

  void _shift(int days) {
    final next = DateTime(_day.year, _day.month, _day.day + days);
    // An attendance change is for today or a later day.
    if (next.isBefore(_today)) return;
    setState(() => _day = next);
  }

  Future<void> _change(AttendanceEntry e) async {
    final status = await showModalBottomSheet<String>(
      context: context,
      builder: (_) => ListView(
        shrinkWrap: true,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(e.name, style: Theme.of(context).textTheme.titleMedium),
          ),
          for (final s in Attendance.all)
            ListTile(
              key: ValueKey('attendance-$s'),
              title: Text(_optionLabel(s)),
              trailing: s == e.status ? const Icon(Symbols.check_rounded) : null,
              onTap: () => Navigator.of(context).pop(s),
            ),
        ],
      ),
    );
    if (status == null || !mounted) return;
    var start = '';
    if (status == Attendance.lateStart) {
      final picked = await showTimePicker(
        context: context,
        helpText: CrewText.chooseLateStart,
        initialTime: const TimeOfDay(hour: 8, minute: 0),
      );
      if (picked == null) return;
      start = '${picked.hour.toString().padLeft(2, '0')}:'
          '${picked.minute.toString().padLeft(2, '0')}';
    }
    try {
      final result = await ref.read(crewRepositoryProvider).managerSetAttendance(
          e.crewId,
          status: status,
          from: _day,
          start: start);
      ref.invalidate(managerAttendanceProvider(apiDate(_day)));
      ref.invalidate(managerScheduleProvider(apiDate(_day)));
      if (!mounted) return;
      final moved = result.released.where((j) => j.reassigned).length;
      final waiting = result.released.length - moved;
      showSnack(
          context,
          result.released.isEmpty
              ? CrewText.attendanceSaved
              : '${CrewText.attendanceSaved} ${CrewText.releasedJobs(moved, waiting)}');
    } catch (err) {
      if (mounted) showSnack(context, failureText(err));
    }
  }

  @override
  Widget build(BuildContext context) {
    final key = apiDate(_day);
    final attendance = ref.watch(managerAttendanceProvider(key));
    return Scaffold(
      appBar: AppBar(title: Text(CrewText.attendance)),
      body: Column(
        children: [
          Row(
            children: [
              IconButton(
                tooltip: CrewText.previousDay,
                icon: const Icon(Symbols.chevron_left_rounded),
                onPressed: _day.isAfter(_today) ? () => _shift(-1) : null,
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
            child: attendance.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => ErrorView(
                message: failureText(e),
                onRetry: () => ref.invalidate(managerAttendanceProvider(key)),
              ),
              data: (a) => a.crew.isEmpty
                  ? Center(child: Text(CrewText.noCrew))
                  : RefreshIndicator(
                      onRefresh: () =>
                          ref.refresh(managerAttendanceProvider(key).future),
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          for (final e in a.crew)
                            Card(
                              key: ValueKey('attendance-${e.crewId}'),
                              child: ListTile(
                                title: Text(e.name),
                                subtitle: Text([
                                  if (e.role.isNotEmpty) e.role,
                                  e.working
                                      ? '${e.start} - ${e.end}'
                                      : CrewText.dayOff,
                                  if (e.openJobs > 0)
                                    CrewText.openJobsCount(e.openJobs),
                                ].join(' · ')),
                                trailing: Text(_statusLabel(e)),
                                onTap: () => _change(e),
                              ),
                            ),
                        ],
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
