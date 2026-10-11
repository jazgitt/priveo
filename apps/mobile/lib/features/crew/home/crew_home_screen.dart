import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';
import '../job/job_card_screen.dart';
import '../manager/manager_schedule_screen.dart';
import '../profile/crew_profile_screen.dart';
import '../upload/upload_queue.dart';
import 'crew_home_data.dart';

/// The crew member's job cards, by day or all so far (CRW-SCH-01, CRW-SCH-06).
class CrewHomeScreen extends ConsumerWidget {
  const CrewHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final day = ref.watch(crewDayProvider);
    final key = visitsKey(day);
    final visits = ref.watch(crewVisitsProvider(key));
    final isManager = ref.watch(crewProfileProvider).value?.isManager ?? false;
    final queued = ref.watch(queuedUploadsProvider).value ?? const [];

    return Scaffold(
      appBar: AppBar(
        title: Text(l.appName),
        actions: [
          if (isManager)
            IconButton(
              tooltip: CrewText.team,
              icon: const Icon(Symbols.groups_rounded),
              onPressed: () =>
                  Navigator.of(context).push(crewRoute(const ManagerScheduleScreen())),
            ),
          IconButton(
            tooltip: CrewText.profile,
            icon: const Icon(Symbols.person_rounded),
            onPressed: () =>
                Navigator.of(context).push(crewRoute(const CrewProfileScreen())),
          ),
          const SignOutButton(),
        ],
      ),
      body: visits.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(crewVisitsProvider(key)),
        ),
        data: (v) => RefreshIndicator(
          onRefresh: () {
            ref.invalidate(crewProfileProvider);
            return ref.refresh(crewVisitsProvider(key).future);
          },
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _DayBar(day: day),
              if (v.society.isNotEmpty) Text(v.society),
              const SizedBox(height: 16),
              Row(
                children: [
                  _Count(l.crewTotal, v.total),
                  const SizedBox(width: 12),
                  _Count(l.crewDone, v.done),
                  const SizedBox(width: 12),
                  _Count(l.crewLeft, v.left),
                ],
              ),
              if (queued.isNotEmpty) ...[
                const SizedBox(height: 12),
                _UploadsBanner(queued),
              ],
              const SizedBox(height: 16),
              if (v.jobs.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 32),
                  child: Center(child: Text(CrewText.noJobs)),
                ),
              for (final job in v.jobs) ...[
                JobCardTile(
                  card: job,
                  showDate: day == null,
                  onTap: () async {
                    await Navigator.of(context)
                        .push(crewRoute(JobCardScreen(jobId: job.id)));
                    ref.invalidate(crewVisitsProvider(key));
                  },
                ),
                const SizedBox(height: 12),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _DayBar extends ConsumerWidget {
  const _DayBar({required this.day});
  final DateTime? day;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final notifier = ref.read(crewDayProvider.notifier);
    final title = day == null
        ? CrewText.allJobs
        : '${l.crewToday} · ${formatDate(day!)}';
    return Row(
      children: [
        IconButton(
          tooltip: CrewText.previousDay,
          icon: const Icon(Symbols.chevron_left_rounded),
          onPressed: day == null ? null : () => notifier.shift(-1),
        ),
        Expanded(
          child: Text(title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge),
        ),
        IconButton(
          tooltip: CrewText.nextDay,
          icon: const Icon(Symbols.chevron_right_rounded),
          onPressed: day == null ? null : () => notifier.shift(1),
        ),
        TextButton(
          onPressed: day == null ? notifier.today : notifier.all,
          child: Text(day == null ? l.crewToday : CrewText.all),
        ),
      ],
    );
  }
}

class _UploadsBanner extends ConsumerWidget {
  const _UploadsBanner(this.queued);
  final List<QueuedUpload> queued;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final failed = queued.where((q) => q.step == UploadStep.failed).length;
    return SectionCard(
      child: Row(
        children: [
          const Icon(Symbols.cloud_upload_rounded),
          const SizedBox(width: 12),
          Expanded(
            child: Text(failed > 0
                ? CrewText.uploadsFailed(failed)
                : CrewText.uploadsWaiting(queued.length)),
          ),
        ],
      ),
    );
  }
}

class _Count extends StatelessWidget {
  const _Count(this.label, this.value);
  final String label;
  final int value;

  @override
  Widget build(BuildContext context) => Expanded(
        child: SectionCard(
          child: Column(
            children: [
              Text('$value', style: Theme.of(context).textTheme.headlineMedium),
              Text(label, style: Theme.of(context).textTheme.labelMedium),
            ],
          ),
        ),
      );
}
