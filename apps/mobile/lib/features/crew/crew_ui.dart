import 'package:flutter/material.dart';

import '../../core/network/api_failure.dart';
import '../../core/ui/theme.dart';
import '../../core/ui/widgets.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../core/util/format.dart';
import '../../l10n/app_localizations.dart';
import 'crew_text.dart';
import 'data/crew_models.dart';

/// A route for a crew screen. Pushed screens sit outside the `/crew` route's
/// theme, so each is wrapped in the crew look (white).
Route<T> crewRoute<T>(Widget screen) => MaterialPageRoute<T>(
    builder: (_) => Theme(data: crewTheme, child: screen));

/// What to tell the crew member about a failed call.
String failureText(Object error) {
  if (error is ApiFailure && error.message != null) return error.message!;
  return CrewText.offline;
}

void showSnack(BuildContext context, String text) =>
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));

ChipTone toneForJob(String status) => switch (status) {
      JobStatus.completed => ChipTone.ok,
      JobStatus.inProgress => ChipTone.info,
      JobStatus.couldNotComplete => ChipTone.warn,
      _ => ChipTone.neutral,
    };

/// One job card: the vehicle, the parking spot, the service, the status and
/// the time to finish by. No customer name or mobile number (CRW-SCH-13).
class JobCardTile extends StatelessWidget {
  const JobCardTile({
    super.key,
    required this.card,
    required this.onTap,
    this.showDate = false,
    this.showAssignee = false,
    this.lockedBy,
  });

  /// When set, the card is locked behind the job of this vehicle (S-13): it
  /// cannot be opened and says "Finish (vehicle) first".
  final String? lockedBy;

  final CrewJobCard card;
  final VoidCallback onTap;
  final bool showDate;
  final bool showAssignee;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final locked = lockedBy != null;
    final lines = <String>[
      [card.parking, card.service].where((p) => p.isNotEmpty).join(' · '),
      if (card.vehicle.name.isNotEmpty && card.vehicle.registration.isNotEmpty)
        card.vehicle.name,
      if (card.startTime != null) formatClock(card.startTime!),
      if (card.finishBy != null) CrewText.finishBy(formatClock(card.finishBy!)),
      if (showDate) formatDate(card.date),
      if (showAssignee && card.assignedTo != null) card.assignedTo!.name,
      if (locked) AppLocalizations.of(context).crewFinishFirst(lockedBy!),
    ];
    return Semantics(
      button: true,
      enabled: !locked,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: locked ? null : onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 56),
          child: SectionCard(
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(card.vehicle.title, style: text.titleSmall),
                      for (final l in lines) Text(l, style: text.bodySmall),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                if (locked)
                  Icon(Symbols.lock_rounded,
                      key: const ValueKey('queue-lock'),
                      color: Theme.of(context).disabledColor)
                else
                  StatusChip(card.status, tone: toneForJob(card.status)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
