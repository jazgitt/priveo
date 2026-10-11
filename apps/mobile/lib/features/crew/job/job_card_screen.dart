import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';
import '../data/crew_models.dart';
import 'could_not_complete_screen.dart';
import 'perform_service_screen.dart';

/// One job: the vehicle, where it is, what to do and by when (CRW-SCH-02,
/// CRW-SCH-04). The customer's name and mobile number are never here.
class JobCardScreen extends ConsumerWidget {
  const JobCardScreen({super.key, required this.jobId});

  final String jobId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(jobDetailProvider(jobId));
    return Scaffold(
      appBar: AppBar(title: Text(CrewText.jobTitle)),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(jobDetailProvider(jobId)),
        ),
        data: (d) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            JobFacts(card: d.job),
            const SizedBox(height: 16),
            if (d.outcome != null) _OutcomeCard(d.outcome!),
            if (d.job.status == JobStatus.completed && d.finishedAt != null)
              SectionCard(
                  child: Text(CrewText.finishedAt(formatDate(d.finishedAt!)))),
            if (!d.job.isClosed) ...[
              PrimaryButton(
                label: d.job.status == JobStatus.scheduled
                    ? CrewText.startJob
                    : CrewText.continueJob,
                onPressed: () => _open(context, ref, d),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () async {
                  final done = await Navigator.of(context).push<bool>(
                      crewRoute(CouldNotCompleteScreen(jobId: jobId)));
                  if (done == true && context.mounted) {
                    ref.invalidate(jobDetailProvider(jobId));
                  }
                },
                child: Text(CrewText.couldNotComplete),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _open(
      BuildContext context, WidgetRef ref, CrewJobDetail d) async {
    final nav = Navigator.of(context);
    if (d.job.status == JobStatus.scheduled) {
      try {
        await ref.read(crewRepositoryProvider).start(jobId);
      } catch (e) {
        if (context.mounted) showSnack(context, failureText(e));
        return;
      }
    }
    await nav.push(crewRoute(PerformServiceScreen(jobId: jobId)));
    ref.invalidate(jobDetailProvider(jobId));
  }
}

/// The details printed on a card, shared by the crew and manager views.
class JobFacts extends StatelessWidget {
  const JobFacts({super.key, required this.card});

  final CrewJobCard card;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    Widget row(String label, String value) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                  width: 110,
                  child: Text(label, style: text.labelMedium)),
              Expanded(child: Text(value)),
            ],
          ),
        );
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                  child: Text(card.vehicle.title,
                      style: text.headlineSmall)),
              StatusChip(card.status, tone: toneForJob(card.status)),
            ],
          ),
          const SizedBox(height: 8),
          row(CrewText.service, card.service),
          if (card.vehicle.name.isNotEmpty) row(CrewText.car, card.vehicle.name),
          if (card.vehicle.category.isNotEmpty)
            row(CrewText.category, card.vehicle.category),
          row(CrewText.society, card.society),
          row(CrewText.parking, card.parking.isEmpty ? '-' : card.parking),
          if (card.startTime != null)
            row(CrewText.slot, formatClock(card.startTime!)),
          if (card.finishBy != null)
            row(CrewText.finishByLabel, formatClock(card.finishBy!)),
          row(CrewText.date, formatDate(card.date)),
          row(CrewText.checklist,
              '${card.checklistDone} / ${card.checklistTotal}'),
          if (card.assignedTo != null)
            row(CrewText.assignedTo, card.assignedTo!.name),
        ],
      ),
    );
  }
}

class _OutcomeCard extends StatelessWidget {
  const _OutcomeCard(this.outcome);
  final JobOutcomeInfo outcome;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: SectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(outcome.kind == 'skipped'
                  ? CrewText.skippedByManager
                  : CrewText.reasonLabel(outcome.reasonKey ?? 'other')),
              if (outcome.note.isNotEmpty) Text(outcome.note),
            ],
          ),
        ),
      );
}
