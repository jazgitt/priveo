import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'capture/media_capture.dart';
import 'data/crew_models.dart';
import 'data/crew_repository.dart';
import 'upload/sqlite_store.dart';
import 'upload/upload_queue.dart';

/// The crew endpoints. Tests override this with a fake.
final crewRepositoryProvider = Provider<CrewRepository>(
    (ref) => ApiCrewRepository(ref.watch(dioProvider)));

/// Uploads go through the same client. Tests override this with a fake.
final uploadApiProvider = Provider<UploadApi>(
    (ref) => ApiCrewRepository(ref.watch(dioProvider)));

final mediaCaptureProvider =
    Provider<MediaCapture>((ref) => DeviceMediaCapture());

final uploadQueueStoreProvider =
    Provider<UploadQueueStore>((ref) => SqliteUploadQueueStore());

/// Emits true each time the phone gets a connection.
final onlineEventsProvider = Provider<Stream<bool>?>((ref) {
  try {
    return Connectivity().onConnectivityChanged.map(
        (results) => results.any((r) => r != ConnectivityResult.none));
  } catch (_) {
    return null;
  }
});

/// The offline upload queue. It starts when first read, which is when the
/// crew home opens, so unsent files go out on app open and again whenever
/// the connection changes (CRW-SVC-10).
final uploadQueueProvider = Provider<UploadQueue>((ref) {
  final queue = UploadQueue(
    api: ref.watch(uploadApiProvider),
    store: ref.watch(uploadQueueStoreProvider),
    online: ref.watch(onlineEventsProvider),
    stash: stashFile,
    discard: discardFile,
  );
  ref.onDispose(queue.dispose);
  unawaited(queue.start());
  return queue;
});

/// What is waiting on the phone, live.
final queuedUploadsProvider = StreamProvider<List<QueuedUpload>>((ref) async* {
  final queue = ref.watch(uploadQueueProvider);
  yield queue.items;
  yield* queue.changes;
});

/// `yyyy-mm-dd` for one day, or `all`.
final crewVisitsProvider = FutureProvider.autoDispose
    .family<CrewVisitList, String>((ref, key) {
  final repo = ref.watch(crewRepositoryProvider);
  return key == 'all'
      ? repo.visits(all: true)
      : repo.visits(date: DateTime.parse(key));
});

final jobDetailProvider = FutureProvider.autoDispose
    .family<CrewJobDetail, String>(
        (ref, id) => ref.watch(crewRepositoryProvider).job(id));

final managerJobProvider = FutureProvider.autoDispose
    .family<CrewJobDetail, String>(
        (ref, id) => ref.watch(crewRepositoryProvider).managerJob(id));

final crewProfileProvider = FutureProvider.autoDispose<CrewProfileInfo>(
    (ref) => ref.watch(crewRepositoryProvider).profile());

final reasonsProvider = FutureProvider.autoDispose<List<CrewReason>>(
    (ref) => ref.watch(crewRepositoryProvider).reasons());

final managerScheduleProvider = FutureProvider.autoDispose
    .family<ManagerSchedule, String>((ref, key) =>
        ref.watch(crewRepositoryProvider).managerSchedule(DateTime.parse(key)));

final managerCrewProvider = FutureProvider.autoDispose<List<CrewRef>>(
    (ref) => ref.watch(crewRepositoryProvider).managerCrew());
