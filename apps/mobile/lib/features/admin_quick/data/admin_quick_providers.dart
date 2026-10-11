import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'admin_quick_models.dart';
import 'admin_quick_repository.dart';

/// The admin home on real data (ADM-ACC-07, MQ-7).
final adminQuickHomeProvider = FutureProvider.autoDispose<QuickHome>(
  (ref) => ref.watch(adminQuickRepositoryProvider).home(),
);

/// The complaints, filtered by status. An empty string means all.
final complaintsProvider = FutureProvider.autoDispose
    .family<List<QuickComplaint>, String>(
      (ref, status) => ref
          .watch(adminQuickRepositoryProvider)
          .complaints(status: status.isEmpty ? null : status),
    );

final complaintProvider = FutureProvider.autoDispose
    .family<QuickComplaint, String>(
      (ref, id) => ref.watch(adminQuickRepositoryProvider).complaint(id),
    );

/// The feedback, filtered by rating. Zero means all.
final feedbackProvider = FutureProvider.autoDispose
    .family<List<QuickFeedback>, int>(
      (ref, rating) => ref
          .watch(adminQuickRepositoryProvider)
          .feedback(rating: rating == 0 ? null : rating),
    );

final ratingsProvider = FutureProvider.autoDispose<QuickRatings>(
  (ref) => ref.watch(adminQuickRepositoryProvider).ratings(),
);

final needsSchedulingProvider = FutureProvider.autoDispose<List<QuickJob>>(
  (ref) => ref.watch(adminQuickRepositoryProvider).needsScheduling(),
);

/// A day and an optional society (empty string for all).
typedef DayKey = ({DateTime date, String societyId});

final dayScheduleProvider = FutureProvider.autoDispose
    .family<DaySchedule, DayKey>(
      (ref, k) => ref
          .watch(adminQuickRepositoryProvider)
          .day(k.date, societyId: k.societyId.isEmpty ? null : k.societyId),
    );

typedef CapacityKey = ({String societyId, DateTime start});

final capacityProvider = FutureProvider.autoDispose
    .family<List<DayCapacity>, CapacityKey>(
      (ref, k) => ref
          .watch(adminQuickRepositoryProvider)
          .capacity(k.societyId, k.start),
    );
