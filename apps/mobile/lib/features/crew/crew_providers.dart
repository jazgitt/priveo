import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../core/providers.dart';
import 'capture/media_capture.dart';
import 'data/crew_models.dart';
import 'data/crew_repository.dart';
import 'data/manager_models.dart';
import 'upload/sqlite_store.dart';
import 'upload/upload_queue.dart';

/// The crew endpoints. Tests override this with a fake.
final crewRepositoryProvider = Provider<CrewRepository>(
    (ref) => ApiCrewRepository(ref.watch(dioProvider)));

/// Uploads use an owner-bound client. Tests override this with a fake.
final crewUploadOwnerProvider = Provider<String?>((ref) {
  final session = ref.watch(authControllerProvider).value;
  return session?.role == Role.crew ? session?.loginId : null;
});

final uploadApiProvider = Provider<UploadApi>((ref) {
  final owner = ref.watch(crewUploadOwnerProvider);
  var active = true;
  // This client can never retry a pending upload with another login's token.
  final dio = buildDio(
    baseUrl: ref.watch(appConfigProvider).apiBaseUrl,
    accessToken: () {
      if (!active) return null;
      final session = ref.read(authControllerProvider).value;
      return owner != null && session?.role == Role.crew && session?.loginId == owner
          ? session?.accessToken : null;
    },
    refreshTokens: () async {
      if (!active || owner == null || ref.read(crewUploadOwnerProvider) != owner) return false;
      final refreshed = await ref.read(authControllerProvider.notifier).refreshTokens();
      return active && refreshed && ref.read(crewUploadOwnerProvider) == owner;
    },
  );
  ref.onDispose(() { active = false; dio.close(force: true); });
  return ApiCrewRepository(dio);
});

final mediaCaptureProvider =
    Provider<MediaCapture>((ref) => DeviceMediaCapture());

final uploadQueueStoreProvider = Provider<UploadQueueStore>((ref) {
  final owner = ref.watch(crewUploadOwnerProvider);
  if (owner == null) throw StateError('Crew sign-in required for uploads');
  return SqliteUploadQueueStore(ownerId: owner);
});

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
  final owner = ref.watch(crewUploadOwnerProvider);
  var active = true;
  final queue = UploadQueue(
    api: ref.watch(uploadApiProvider),
    store: ref.watch(uploadQueueStoreProvider),
    online: ref.watch(onlineEventsProvider),
    ownerId: owner,
    isCurrent: () => active && owner != null && ref.read(crewUploadOwnerProvider) == owner,
    stash: (path) => stashFile(path, ownerId: owner),
    discard: discardFile,
  );
  ref.onDispose(() { active = false; queue.dispose(); });
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

/// `yyyy-mm-dd` for the day of the attendance list.
final managerAttendanceProvider = FutureProvider.autoDispose
    .family<AttendanceDay, String>((ref, key) =>
        ref.watch(crewRepositoryProvider).managerAttendance(DateTime.parse(key)));

final managerHoursProvider = FutureProvider.autoDispose<List<CrewHours>>(
    (ref) => ref.watch(crewRepositoryProvider).managerHours());

final managerReassignOptionsProvider = FutureProvider.autoDispose
    .family<List<ReassignOption>, String>((ref, jobId) =>
        ref.watch(crewRepositoryProvider).managerReassignOptions(jobId));
