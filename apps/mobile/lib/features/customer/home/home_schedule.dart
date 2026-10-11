import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/api/api.g.dart' show VehicleCard;
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../support/data/support_models.dart' show PendingCheckIn;
import '../../support/data/support_repository.dart';
import '../../support/routes.dart' show SupportRoutes;
import '../calendar/calendar_strings.dart';
import '../data/customer_reads_repository.dart';

/// The time Home uses for its greeting and its "Tomorrow" label. Tests
/// override it.
final homeNowProvider = Provider<DateTime Function()>((ref) => DateTime.now);

/// The check-ins due now. A failed look-up is an empty list: Home keeps
/// working without the card.
final homeCheckInsProvider = FutureProvider.autoDispose<List<PendingCheckIn>>((
  ref,
) async {
  try {
    return await ref.watch(supportRepositoryProvider).pendingCheckIns();
  } catch (_) {
    return const [];
  }
});

/// "Good morning," and so on, by the hour (HOME-01).
String greetingFor(DateTime now) => now.hour < 12
    ? CalStrings.goodMorning
    : now.hour < 17
    ? CalStrings.goodAfternoon
    : CalStrings.goodEvening;

/// The date line of the next service card: "Tomorrow, Wed 07-Oct-26" for
/// today and tomorrow, and `dd-Mon-yy` after that (HOME-04).
String nextServiceDateLabel(DateTime date, DateTime now) {
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(date.year, date.month, date.day);
  final diff = day.difference(today).inDays;
  final plain = formatDate(day);
  if (diff == 0 || diff == 1) {
    final name = diff == 0 ? CalStrings.today : CalStrings.tomorrow;
    return '$name, ${DateFormat('EEE').format(day)} $plain';
  }
  return plain;
}

class GreetingLine extends ConsumerWidget {
  const GreetingLine({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Text(
    greetingFor(ref.watch(homeNowProvider)()),
    style: Theme.of(
      context,
    ).textTheme.bodyMedium?.copyWith(color: context.brand.mute),
  );
}

/// The next visit for the selected vehicle (HOME-04). Without a visit it
/// shows the customer's service time and interior care day. Once the visit
/// is assigned it adds the crew member and time (CAL-10).
class NextServiceCard extends ConsumerWidget {
  const NextServiceCard(this.vehicle, {super.key, required this.onCalendar});

  final VehicleCard vehicle;
  final VoidCallback onCalendar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final fromVisits = ref
        .watch(nextServicesProvider)
        .value
        ?.where((n) => n.vehicleId == vehicle.id)
        .firstOrNull;
    final home = vehicle.nextService;
    final DateTime? date = home?.date ?? fromVisits?.date;
    final status = home?.status ?? fromVisits?.status;
    final services = fromVisits != null && fromVisits.services.isNotEmpty
        ? fromVisits.services
        : [
            if ((home?.service ?? fromVisits?.service ?? '').isNotEmpty)
              (home?.service ?? fromVisits!.service),
          ];
    final cutoff = fromVisits?.cutoffTime ?? vehicle.cutoffTime;
    final day = vehicle.interiorDay;
    Widget detail(String service, String value) => Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        children: [
          ServiceMarker(service),
          const SizedBox(width: 8),
          Expanded(
            child: Text(value, style: text.bodyMedium?.copyWith(color: b.mute)),
          ),
        ],
      ),
    );
    final crew = fromVisits?.crewName;
    final start = fromVisits?.startTime;
    return SectionCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: SectionLabel(l.nextService)),
              if (status != null)
                StatusChip(status, tone: StatusChip.toneFor(status)),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            date == null
                ? l.notScheduledYet
                : nextServiceDateLabel(date, ref.watch(homeNowProvider)()),
            style: text.headlineSmall,
          ),
          for (final s in services) detail(s, s),
          if (crew != null && start != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(
                children: [
                  Icon(Symbols.person_rounded, size: 14, color: b.mute),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      CalStrings.crewAt(
                        crew,
                        formatClock(start),
                        formatClock(fromVisits!.endTime ?? start),
                      ),
                      style: text.bodyMedium?.copyWith(color: b.mute),
                    ),
                  ),
                ],
              ),
            ),
          if (cutoff != null)
            detail('Cleaning-External', l.dailyCleanBy(formatClock(cutoff))),
          if (day != null) detail('Cleaning-Internal', l.interiorCareOn(day)),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onCalendar,
              icon: const Icon(Symbols.calendar_month_rounded, size: 18),
              label: Text(l.viewCalendar),
            ),
          ),
        ],
      ),
    );
  }
}

/// The prototype's service markers: a green dot for exterior, a blue square
/// for interior, a violet star for Deep Spa.
class ServiceMarker extends StatelessWidget {
  const ServiceMarker(this.service, {super.key});

  final String service;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final s = service.toLowerCase();
    if (s.contains('spa')) {
      return Icon(Symbols.star_rounded, size: 12, color: b.spa, fill: 1);
    }
    final interior = s.contains('internal') || s.contains('interior');
    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        color: interior ? b.info : b.ok,
        borderRadius: BorderRadius.circular(interior ? 2 : 4),
      ),
    );
  }
}

/// The "Monthly check-in" card (HOME-08, CHK-08). It shows from four days
/// before renewal until the check-in is given, even with notifications off.
class MonthlyCheckInCard extends ConsumerWidget {
  const MonthlyCheckInCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pending = ref.watch(homeCheckInsProvider).value ?? const [];
    if (pending.isEmpty) return const SizedBox.shrink();
    final first = pending.first;
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
      child: SectionCard(
        child: InkWell(
          onTap: () => context.push(
            '${SupportRoutes.checkin}?subscription=${first.subscriptionId}',
          ),
          child: Row(
            children: [
              Icon(Symbols.rate_review_rounded, color: b.gold),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(CalStrings.monthlyCheckIn, style: text.titleSmall),
                    Text(
                      pending.length > 1
                          ? '${first.vehicleLabel} and ${pending.length - 1} more'
                          : first.vehicleLabel,
                      style: text.bodyMedium?.copyWith(color: b.mute),
                    ),
                  ],
                ),
              ),
              const Icon(Symbols.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}
