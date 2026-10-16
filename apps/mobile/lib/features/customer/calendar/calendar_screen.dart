import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/read_refresh.dart';
import 'package:intl/intl.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../cust_strings.dart';
import 'calendar_strings.dart';
import 'day_card.dart';
import '../data/customer_reads_repository.dart';
import '../home/customer_home_data.dart';

/// The marker of a day (CAL-02).
enum DayMarker {
  done,
  doneInterior,
  spa,
  scheduled,
  scheduledInterior,
  scheduledSpa,
  expected,
  skipped,
  paused,
  missed,
}

/// The marker for the visits of one date, or null when there are none.
DayMarker? dayMarkerFor(List<CalendarVisit> visits) {
  if (visits.isEmpty) return null;
  bool any(bool Function(CalendarVisit) f) => visits.any(f);
  if (any((v) => v.status == 'Missed')) return DayMarker.missed;
  if (visits.every((v) => v.status == 'Skipped')) return DayMarker.skipped;
  if (visits.every((v) => v.status == 'Paused')) return DayMarker.paused;
  bool hasService(Iterable<CalendarVisit> vs, String s) =>
      vs.any((v) => v.services.any((x) => x.toLowerCase().contains(s)));
  final done = visits.where((v) => v.status == 'Completed').toList();
  if (done.isEmpty) {
    // An upcoming day: outlined, with the interior or spa shape (CAL-02).
    final open = visits
        .where((v) => v.status != 'Skipped' && v.status != 'Paused')
        .toList();
    if (hasService(open, 'spa')) return DayMarker.scheduledSpa;
    if (hasService(open, 'internal') || hasService(open, 'interior')) {
      return DayMarker.scheduledInterior;
    }
    return open.every((v) => v.projected)
        ? DayMarker.expected
        : DayMarker.scheduled;
  }
  if (hasService(done, 'spa')) return DayMarker.spa;
  if (hasService(done, 'internal') || hasService(done, 'interior')) {
    return DayMarker.doneInterior;
  }
  return DayMarker.done;
}

/// The service calendar tab (CAL-01 to CAL-06). It is a body, not a page: the
/// customer shell supplies the scaffold. It follows the vehicle selected on
/// Home (HOME-07).
class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key, this.today});

  /// For tests. The real date is used when it is null.
  final DateTime? today;

  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  late final DateTime _today = _dateOnly(widget.today ?? DateTime.now());
  late DateTime _month = DateTime(_today.year, _today.month);
  late DateTime _selected = _today;

  static DateTime _dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

  void _move(int months) => setState(() {
    _month = DateTime(_month.year, _month.month + months);
    _selected = _month.year == _today.year && _month.month == _today.month
        ? _today
        : _month;
  });

  @override
  Widget build(BuildContext context) {
    final home = ref.watch(customerHomeProvider).value;
    String? vehicleId;
    if (home != null && home.vehicles.isNotEmpty) {
      vehicleId = home
          .vehicles[selectedIndex(
            home.vehicles,
            ref.watch(selectedVehicleProvider),
          )]
          .id;
    }
    final key = (
      month: DateFormat('yyyy-MM').format(_month),
      vehicleId: vehicleId,
    );
    final month = ref.watch(calendarMonthProvider(key));
    final text = Theme.of(context).textTheme;
    return month.when(
      skipLoadingOnReload: true,
      skipError: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => ErrorView(
        message: e is ApiFailure ? e.message : null,
        onRetry: () => ref.invalidate(calendarMonthProvider(key)),
      ),
      data: (data) {
        final byDate = <DateTime, List<CalendarVisit>>{};
        for (final v in data.visits) {
          byDate.putIfAbsent(_dateOnly(v.date), () => []).add(v);
        }
        final dayVisits = byDate[_selected] ?? const <CalendarVisit>[];
        String? cutoff;
        if (home != null && dayVisits.isNotEmpty) {
          for (final v in home.vehicles) {
            if (v.id == dayVisits.first.vehicleId) cutoff = v.cutoffTime;
          }
        }
        final renewal = data.renewals
            .where((r) => _dateOnly(r.date) == _selected)
            .firstOrNull
            ?.date;
        return RefreshIndicator(
          onRefresh: () => refreshAll(ref, () => ref.read(calendarMonthProvider(key).future)),
          child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 110),
          children: [
            Text(CustStrings.calendarTitle, style: text.displaySmall),
            const SizedBox(height: 14),
            Row(
              children: [
                IconButton(
                  tooltip: CustStrings.previousMonth,
                  onPressed: () => _move(-1),
                  icon: const Icon(Symbols.chevron_left_rounded),
                ),
                Expanded(
                  child: Text(
                    DateFormat('MMMM yyyy').format(_month),
                    textAlign: TextAlign.center,
                    style: text.titleLarge,
                  ),
                ),
                IconButton(
                  tooltip: CustStrings.nextMonth,
                  onPressed: () => _move(1),
                  icon: const Icon(Symbols.chevron_right_rounded),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _MonthGrid(
              month: _month,
              today: _today,
              selected: _selected,
              byDate: byDate,
              onSelected: (d) => setState(() => _selected = d),
            ),
            const SizedBox(height: 14),
            const _Legend(),
            const SizedBox(height: 18),
            DayCard(
              date: _selected,
              visits: dayVisits,
              fallbackCutoff: cutoff,
              today: _today,
              renewal: renewal,
            ),
          ],
        ),
        );
      },
    );
  }
}

class _MonthGrid extends StatelessWidget {
  const _MonthGrid({
    required this.month,
    required this.today,
    required this.selected,
    required this.byDate,
    required this.onSelected,
  });

  final DateTime month;
  final DateTime today;
  final DateTime selected;
  final Map<DateTime, List<CalendarVisit>> byDate;
  final ValueChanged<DateTime> onSelected;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    // Monday first: DateTime.weekday is 1 for Monday.
    final lead = DateTime(month.year, month.month, 1).weekday - 1;
    final days = DateUtils.getDaysInMonth(month.year, month.month);
    final cells = <DateTime?>[
      for (var i = 0; i < lead; i++) null,
      for (var d = 1; d <= days; d++) DateTime(month.year, month.month, d),
    ];
    while (cells.length % 7 != 0) {
      cells.add(null);
    }
    const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return Column(
      children: [
        Row(
          children: [
            for (final n in names)
              Expanded(
                child: Center(
                  child: Text(
                    n,
                    style: text.labelSmall?.copyWith(color: b.mute),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 6),
        for (var row = 0; row < cells.length; row += 7)
          Row(
            children: [
              for (final d in cells.sublist(row, row + 7))
                Expanded(
                  child: d == null
                      ? const SizedBox(height: 54)
                      : _DayCell(
                          date: d,
                          isToday: d == today,
                          isSelected: d == selected,
                          marker: dayMarkerFor(byDate[d] ?? const []),
                          onTap: () => onSelected(d),
                        ),
                ),
            ],
          ),
      ],
    );
  }
}

class _DayCell extends StatelessWidget {
  const _DayCell({
    required this.date,
    required this.isToday,
    required this.isSelected,
    required this.marker,
    required this.onTap,
  });

  final DateTime date;
  final bool isToday;
  final bool isSelected;
  final DayMarker? marker;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    return Semantics(
      button: true,
      selected: isSelected,
      label: formatDate(date),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          height: 54,
          margin: const EdgeInsets.all(2),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: isSelected ? b.gold.withValues(alpha: 0.16) : null,
            border: Border.all(
              color: isSelected
                  ? b.gold
                  : isToday
                  ? b.goldText
                  : Colors.transparent,
            ),
          ),
          child: ExcludeSemantics(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  '${date.day}',
                  style: text.bodyMedium?.copyWith(
                    fontWeight: isToday ? FontWeight.w800 : FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                SizedBox(
                  height: 10,
                  child: marker == null ? null : MarkerDot(marker!),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// The small mark under a date, drawn from shape and colour.
class MarkerDot extends StatelessWidget {
  const MarkerDot(this.marker, {super.key});

  final DayMarker marker;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    switch (marker) {
      case DayMarker.spa:
        return Icon(Symbols.star_rounded, size: 11, color: b.spa, fill: 1);
      case DayMarker.doneInterior:
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _shape(b.ok, filled: true),
            const SizedBox(width: 3),
            _shape(b.info, filled: true, square: true),
          ],
        );
      case DayMarker.done:
        return _shape(b.ok, filled: true);
      case DayMarker.scheduled:
        return _shape(b.info, filled: false);
      case DayMarker.scheduledInterior:
        return _shape(b.info, filled: false, square: true);
      case DayMarker.scheduledSpa:
        return Icon(Symbols.star_rounded, size: 11, color: b.spa, fill: 0);
      case DayMarker.expected:
        return Opacity(opacity: 0.55, child: _shape(b.info, filled: false));
      case DayMarker.paused:
        return Icon(Symbols.pause_rounded, size: 11, color: b.mute);
      case DayMarker.skipped:
        return Container(width: 9, height: 2, color: b.mute);
      case DayMarker.missed:
        return Icon(Symbols.close_rounded, size: 11, color: b.warn);
    }
  }

  static Widget _shape(
    Color color, {
    required bool filled,
    bool square = false,
  }) => Container(
    width: 7,
    height: 7,
    decoration: BoxDecoration(
      color: filled ? color : null,
      border: filled ? null : Border.all(color: color, width: 1.5),
      borderRadius: BorderRadius.circular(square ? 2 : 4),
    ),
  );
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    Widget item(DayMarker m, String label) => Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        MarkerDot(m),
        const SizedBox(width: 6),
        Text(label, style: text.bodySmall?.copyWith(color: b.mute)),
      ],
    );
    return Wrap(
      spacing: 14,
      runSpacing: 8,
      children: [
        item(DayMarker.done, CustStrings.legendDone),
        item(DayMarker.doneInterior, CustStrings.legendInterior),
        item(DayMarker.spa, CustStrings.legendSpa),
        item(DayMarker.scheduled, CustStrings.legendScheduled),
        item(DayMarker.skipped, CustStrings.legendSkipped),
        item(DayMarker.missed, CustStrings.legendMissed),
        item(DayMarker.paused, CalStrings.legendPaused),
        item(DayMarker.expected, CalStrings.legendExpected),
      ],
    );
  }
}
