import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/features/feature_flags.dart';
import '../../../core/features/feature_keys.dart';
import '../crew_providers.dart';
import '../crew_ui.dart';
import '../data/crew_repository.dart';
import 'job_card_screen.dart';

/// The next open job after [jobId] in the crew member's queue for its date, or
/// null (S-13). Only used while the sequential queue is on.
Future<String?> nextOpenJobId(CrewRepository repo, String jobId) async {
  final detail = await repo.job(jobId);
  final list = await repo.visits(date: detail.job.date);
  final at = list.jobs.indexWhere((c) => c.id == jobId);
  if (at < 0) return null;
  for (final c in list.jobs.skip(at + 1)) {
    if (!c.isClosed) return c.id;
  }
  return null;
}

/// Whether a later job is waiting, so the button reads "Save & Next".
final hasNextJobProvider = FutureProvider.autoDispose.family<bool, String>(
    (ref, jobId) async {
  if (!ref.watch(featureOnProvider(FeatureKeys.sequentialQueue))) return false;
  try {
    return await nextOpenJobId(ref.read(crewRepositoryProvider), jobId) != null;
  } catch (_) {
    return false;
  }
});

/// After a job is saved: go to the next job when there is one, otherwise just
/// close the screen as before.
Future<void> afterSave(WidgetRef ref, BuildContext context, String jobId) async {
  final nav = Navigator.of(context);
  String? next;
  if (ref.read(featureOnProvider(FeatureKeys.sequentialQueue))) {
    try {
      next = await nextOpenJobId(ref.read(crewRepositoryProvider), jobId);
    } catch (_) {
      next = null;
    }
  }
  if (next == null) {
    nav.pop(true);
    return;
  }
  nav.popUntil((r) => r.isFirst);
  nav.push(crewRoute(JobCardScreen(jobId: next)));
}
