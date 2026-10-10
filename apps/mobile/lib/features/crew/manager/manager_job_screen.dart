import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';
import '../job/could_not_complete_screen.dart';
import '../job/job_card_screen.dart';

/// A Manager's view of another crew member's job: mark it could not
/// complete, skip it, or reassign it (CRW-MGR-02, CRW-MGR-03).
class ManagerJobScreen extends ConsumerStatefulWidget {
  const ManagerJobScreen({super.key, required this.jobId});

  final String jobId;

  @override
  ConsumerState<ManagerJobScreen> createState() => _State();
}

class _State extends ConsumerState<ManagerJobScreen> {
  bool _busy = false;

  Future<void> _run(Future<void> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      await action();
      ref.invalidate(managerJobProvider(widget.jobId));
      if (mounted) showSnack(context, done);
    } catch (e) {
      if (mounted) showSnack(context, failureText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _skip() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(CrewText.skipJob),
        content: Text(CrewText.skipJobBody),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(CrewText.cancel)),
          TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text(CrewText.skipJob)),
        ],
      ),
    );
    if (ok != true) return;
    await _run(() => ref.read(crewRepositoryProvider).managerSkip(widget.jobId),
        CrewText.jobSkipped);
  }

  Future<void> _reassign(String? currentId) async {
    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (_) => Consumer(
        builder: (context, ref, _) {
          final crew = ref.watch(managerCrewProvider);
          return crew.when(
            loading: () => const SizedBox(
                height: 160,
                child: Center(child: CircularProgressIndicator())),
            error: (e, _) => ErrorView(
                message: failureText(e),
                onRetry: () => ref.invalidate(managerCrewProvider)),
            data: (list) => ListView(
              shrinkWrap: true,
              children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(CrewText.reassignTo,
                      style: Theme.of(context).textTheme.titleMedium),
                ),
                for (final c in list.where((c) => c.id != currentId))
                  ListTile(
                    key: ValueKey('assign-${c.id}'),
                    title: Text(c.name),
                    onTap: () => Navigator.of(context).pop(c.id),
                  ),
              ],
            ),
          );
        },
      ),
    );
    if (choice == null) return;
    await _run(
        () => ref
            .read(crewRepositoryProvider)
            .managerReassign(widget.jobId, choice),
        CrewText.jobReassigned);
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(managerJobProvider(widget.jobId));
    return Scaffold(
      appBar: AppBar(title: Text(CrewText.jobTitle)),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(managerJobProvider(widget.jobId)),
        ),
        data: (d) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            JobFacts(card: d.job),
            const SizedBox(height: 16),
            if (d.outcome != null)
              SectionCard(
                child: Text(d.outcome!.kind == 'skipped'
                    ? CrewText.skippedByManager
                    : CrewText.reasonLabel(d.outcome!.reasonKey ?? 'other')),
              ),
            if (!d.job.isClosed) ...[
              PrimaryButton(
                label: CrewText.reassign,
                busy: _busy,
                onPressed: () => _reassign(d.job.assignedTo?.id),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: _busy
                    ? null
                    : () async {
                        final done = await Navigator.of(context).push<bool>(
                            crewRoute(CouldNotCompleteScreen(
                                jobId: widget.jobId, manager: true)));
                        if (done == true) {
                          ref.invalidate(managerJobProvider(widget.jobId));
                        }
                      },
                child: Text(CrewText.couldNotComplete),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: _busy ? null : _skip,
                child: Text(CrewText.skipJob),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
