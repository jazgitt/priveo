import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import 'crew_home_data.dart';

class CrewHomeScreen extends ConsumerWidget {
  const CrewHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final home = ref.watch(crewHomeProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l.appName),
        actions: const [SignOutButton()],
      ),
      body: home.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            ErrorView(onRetry: () => ref.invalidate(crewHomeProvider)),
        data: (h) => RefreshIndicator(
          onRefresh: () => ref.refresh(crewHomeProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('${l.crewToday} · ${formatDate(h.date)}',
                  style: Theme.of(context).textTheme.headlineMedium),
              Text(h.society),
              const SizedBox(height: 16),
              Row(
                children: [
                  _Count(l.crewTotal, h.total),
                  const SizedBox(width: 12),
                  _Count(l.crewDone, h.done),
                  const SizedBox(width: 12),
                  _Count(l.crewLeft, h.left),
                ],
              ),
              const SizedBox(height: 16),
              for (final j in h.jobs) ...[
                _JobTile(j),
                const SizedBox(height: 12),
              ],
            ],
          ),
        ),
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

class _JobTile extends StatelessWidget {
  const _JobTile(this.job);
  final JobCard job;

  @override
  Widget build(BuildContext context) => ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 56),
        child: SectionCard(
          child: Row(
            children: [
              Text(job.time, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(job.vehicle,
                        style: Theme.of(context).textTheme.titleSmall),
                    Text('${job.parking} · ${job.service}'),
                  ],
                ),
              ),
              StatusChip(job.status, tone: StatusChip.toneFor(job.status)),
            ],
          ),
        ),
      );
}
