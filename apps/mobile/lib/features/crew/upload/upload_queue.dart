import 'dart:async';
import 'dart:convert';

import '../../../core/network/api_failure.dart';
import '../data/crew_models.dart';
import '../data/crew_repository.dart';

/// Where a queued file has got to. The step is saved after each stage, so
/// the queue resumes where it left off after the app closes (CRW-SVC-10).
enum UploadStep {
  /// Waiting to ask the API for a signed URL.
  queued,

  /// The URL is known. The bytes are not sent yet.
  requested,

  /// The bytes are sent. The API has not confirmed them yet.
  sent,

  /// Gave up after repeated server errors. The crew member can retry.
  failed,
}

class QueuedUpload {
  const QueuedUpload({
    required this.id,
    required this.jobId,
    required this.kind,
    required this.stage,
    required this.path,
    required this.contentType,
    required this.sizeBytes,
    this.uploadId,
    this.ticket,
    this.step = UploadStep.queued,
    this.attempts = 0,
    this.lastError,
    this.ownerId,
  });

  final int id;
  final String jobId;

  /// `photo` or `video`.
  final String kind;

  /// Before, During or After.
  final String stage;
  final String path;
  final String contentType;
  final int sizeBytes;
  final String? uploadId;
  final UploadTicket? ticket;
  final UploadStep step;
  final int attempts;
  final String? lastError;
  final String? ownerId;

  QueuedUpload copyWith({
    String? uploadId,
    UploadTicket? ticket,
    UploadStep? step,
    int? attempts,
    String? lastError,
    bool clearTicket = false,
  }) =>
      QueuedUpload(
        id: id,
        jobId: jobId,
        kind: kind,
        stage: stage,
        path: path,
        contentType: contentType,
        sizeBytes: sizeBytes,
        uploadId: clearTicket ? null : (uploadId ?? this.uploadId),
        ticket: clearTicket ? null : (ticket ?? this.ticket),
        step: step ?? this.step,
        attempts: attempts ?? this.attempts,
        lastError: lastError,
        ownerId: ownerId,
      );

  Map<String, Object?> toRow() => {
        'id': id,
        'job_id': jobId,
        'kind': kind,
        'stage': stage,
        'path': path,
        'content_type': contentType,
        'size_bytes': sizeBytes,
        'upload_id': uploadId,
        'upload_url': ticket?.url,
        'method': ticket?.method,
        'headers': ticket == null ? null : jsonEncode(ticket!.headers),
        'step': step.name,
        'attempts': attempts,
        'last_error': lastError,
        'owner_login_id': ownerId,
      };

  factory QueuedUpload.fromRow(Map<String, Object?> r) {
    final uploadId = r['upload_id'] as String?;
    final url = r['upload_url'] as String?;
    return QueuedUpload(
      id: r['id'] as int,
      jobId: r['job_id'] as String,
      kind: r['kind'] as String,
      stage: r['stage'] as String,
      path: r['path'] as String,
      contentType: r['content_type'] as String,
      sizeBytes: r['size_bytes'] as int,
      uploadId: uploadId,
      ticket: (uploadId != null && url != null)
          ? UploadTicket(
              id: uploadId,
              url: url,
              method: (r['method'] as String?) ?? 'PUT',
              headers: ((jsonDecode((r['headers'] as String?) ?? '{}') as Map)
                  .cast<String, String>()),
            )
          : null,
      step: UploadStep.values.firstWhere((s) => s.name == r['step'],
          orElse: () => UploadStep.queued),
      attempts: (r['attempts'] as int?) ?? 0,
      lastError: r['last_error'] as String?,
      ownerId: r['owner_login_id'] as String?,
    );
  }
}

/// Persistent storage for the queue. The phone uses SQLite. Tests use memory.
abstract class UploadQueueStore {
  Future<List<QueuedUpload>> all();

  /// Saves a new item and returns it with its ID.
  Future<QueuedUpload> add(QueuedUpload draft);
  Future<void> update(QueuedUpload item);
  Future<void> remove(int id);
}

class MemoryUploadQueueStore implements UploadQueueStore {
  final Map<int, QueuedUpload> _rows = {};
  int _next = 1;

  @override
  Future<List<QueuedUpload>> all() async =>
      (_rows.values.toList()..sort((a, b) => a.id.compareTo(b.id)));

  @override
  Future<QueuedUpload> add(QueuedUpload draft) async {
    final saved = QueuedUpload(
      id: _next++,
      jobId: draft.jobId,
      kind: draft.kind,
      stage: draft.stage,
      path: draft.path,
      contentType: draft.contentType,
      sizeBytes: draft.sizeBytes,
      ownerId: draft.ownerId,
    );
    _rows[saved.id] = saved;
    return saved;
  }

  @override
  Future<void> update(QueuedUpload item) async => _rows[item.id] = item;

  @override
  Future<void> remove(int id) async => _rows.remove(id);
}

/// Sends photos and videos to the API one at a time, whenever there is a
/// connection. Nothing is lost when the connection drops or the app closes:
/// each file stays on the phone until the API has confirmed it.
class UploadQueue {
  UploadQueue({
    required this.api,
    required this.store,
    this.online,
    this.retryAfter = const Duration(seconds: 30),
    this.maxAttempts = 6,
    this.ownerId,
    bool Function()? isCurrent,
    Future<String> Function(String path)? stash,
    Future<void> Function(String path)? discard,
  })  : _stash = stash ?? ((p) async => p),
        _discard = discard ?? ((_) async {}),
        _isCurrent = isCurrent ?? (() => true);

  final UploadApi api;
  final UploadQueueStore store;

  /// Emits true each time the phone gets a connection.
  final Stream<bool>? online;

  /// How long to wait before trying again after a failure. Zero turns the
  /// timer off (tests).
  final Duration retryAfter;
  final int maxAttempts;
  final String? ownerId;
  final bool Function() _isCurrent;
  bool get _active => !_disposed && _isCurrent();

  void _requireActive() {
    if (!_active) {
      throw const ApiFailure(code: 'signed_out',
          message: 'Sign in to continue the upload.', statusCode: 401);
    }
  }
  final Future<String> Function(String path) _stash;
  final Future<void> Function(String path) _discard;

  final _changes = StreamController<List<QueuedUpload>>.broadcast();
  final _uploaded = StreamController<String>.broadcast();
  StreamSubscription<bool>? _onlineSub;
  Timer? _timer;
  List<QueuedUpload> _items = const [];
  bool _draining = false;
  bool _rerun = false;
  bool _disposed = false;

  List<QueuedUpload> get items => _items;
  Stream<List<QueuedUpload>> get changes => _changes.stream;

  /// The job ID of each upload the API has just confirmed.
  Stream<String> get uploaded => _uploaded.stream;

  int waitingFor(String jobId) =>
      _items.where((i) => i.jobId == jobId).length;

  /// Loads what is on the phone and starts sending. Called when the app
  /// opens and again whenever the connection comes back.
  Future<void> start() async {
    try {
      _items = (await store.all()).where((i) => i.ownerId == ownerId).toList();
    } catch (_) {
      _items = const [];
    }
    _publish();
    if (!_active) return;
    _onlineSub ??= online?.listen((isOnline) {
      if (isOnline) drain();
    }, onError: (_) {});
    await drain();
  }

  /// Keeps a copy of the file and queues it.
  Future<QueuedUpload> enqueue({
    required String jobId,
    required String kind,
    required String stage,
    required String path,
    required String contentType,
    required int sizeBytes,
  }) async {
    _requireActive();
    final kept = await _stash(path);
    if (!_active) {
      await _discard(kept);
      _requireActive();
    }
    final saved = await store.add(QueuedUpload(
      id: 0,
      jobId: jobId,
      kind: kind,
      stage: stage,
      path: kept,
      contentType: contentType,
      sizeBytes: sizeBytes,
      ownerId: ownerId,
    ));
    _items = [..._items, saved];
    _publish();
    unawaited(drain());
    return saved;
  }

  /// Sends a file straight away, without queueing: for a photo that must be
  /// confirmed before the next step (the could-not-complete photo, the
  /// profile photo). Returns the confirmed upload's ID.
  Future<String> sendNow({
    required String purpose,
    String? jobId,
    required String kind,
    String? stage,
    required String path,
    required String contentType,
    required int sizeBytes,
  }) async {
    _requireActive();
    final ticket = await api.requestUpload(
        purpose: purpose,
        jobId: jobId,
        kind: kind,
        stage: stage,
        contentType: contentType,
        sizeBytes: sizeBytes);
    _requireActive();
    await api.sendFile(ticket, path);
    _requireActive();
    await api.confirm(ticket.id);
    return ticket.id;
  }

  /// Puts a failed item back in line.
  Future<void> retry(int id) async {
    _requireActive();
    final i = _items.indexWhere((e) => e.id == id);
    if (i < 0) return;
    await _save(_items[i].copyWith(step: UploadStep.queued, attempts: 0));
    unawaited(drain());
  }

  /// Takes an item off the phone for good, for a file that cannot be sent.
  /// The crew member can take the photo or video again.
  Future<void> remove(int id) async {
    final i = _items.indexWhere((e) => e.id == id);
    if (i < 0) return;
    final item = _items[i];
    await store.remove(id);
    _items = _items.where((e) => e.id != id).toList();
    _publish();
    await _discard(item.path);
  }

  /// Sends every waiting item, in order. Stops at the first sign that the
  /// connection is gone, and tries again when it comes back.
  Future<void> drain() async {
    if (!_active) return;
    if (_draining) {
      _rerun = true;
      return;
    }
    _draining = true;
    try {
      do {
        _rerun = false;
        for (final item in List<QueuedUpload>.of(_items)) {
          if (!_active) return;
          if (item.step == UploadStep.failed) continue;
          final keepGoing = await _process(item);
          if (!keepGoing) break;
        }
      } while (_rerun);
    } finally {
      _draining = false;
      _scheduleRetry();
    }
  }

  /// Returns false when the whole run should stop (offline, signed out).
  Future<bool> _process(QueuedUpload start) async {
    var item = start;
    try {
      _requireActive();
      if (item.step == UploadStep.queued) {
        final ticket = await api.requestUpload(
          purpose: 'proof',
          jobId: item.jobId,
          kind: item.kind,
          stage: item.stage,
          contentType: item.contentType,
          sizeBytes: item.sizeBytes,
        );
        item = item.copyWith(
            step: UploadStep.requested, uploadId: ticket.id, ticket: ticket);
        await _save(item);
        if (!_active) return false;
      }
      if (item.step == UploadStep.requested) {
        await api.sendFile(item.ticket!, item.path);
        item = item.copyWith(step: UploadStep.sent);
        await _save(item);
        if (!_active) return false;
      }
      if (item.step == UploadStep.sent) {
        await api.confirm(item.uploadId!);
        await store.remove(item.id);
        _items = _items.where((e) => e.id != item.id).toList();
        _publish();
        await _discard(item.path);
        if (!_uploaded.isClosed) _uploaded.add(item.jobId);
      }
      return true;
    } on ApiFailure catch (e) {
      if (!_active) return false;
      // No connection, or signed out: wait. Nothing is counted against the file.
      if (e.isNetwork || e.statusCode == 401) return false;
      // The signed link ran out (403), or the storage it points to no longer
      // knows it (404, for example after the storage moved). Ask for a new one.
      if ((e.statusCode == 403 || e.statusCode == 404) &&
          item.step == UploadStep.requested) {
        await _save(item.copyWith(step: UploadStep.queued, clearTicket: true));
        return true;
      }
      // The API lost the request (404 on confirm): start the file again.
      if (e.statusCode == 404 && item.step == UploadStep.sent) {
        await _save(item.copyWith(step: UploadStep.queued, clearTicket: true));
        return true;
      }
      final permanent =
          e.statusCode != null && e.statusCode! >= 400 && e.statusCode! < 500;
      final attempts = item.attempts + 1;
      await _save(item.copyWith(
        attempts: attempts,
        lastError: e.message ?? e.code,
        step: (permanent || attempts >= maxAttempts)
            ? UploadStep.failed
            : item.step,
      ));
      return true;
    } catch (e) {
      if (!_active) return false;
      // The file itself could not be read, for example. Park it.
      await _save(item.copyWith(
          attempts: item.attempts + 1,
          lastError: '$e',
          step: UploadStep.failed));
      return true;
    }
  }

  Future<void> _save(QueuedUpload item) async {
    await store.update(item);
    _items = [for (final e in _items) e.id == item.id ? item : e];
    _publish();
  }

  void _publish() {
    if (!_changes.isClosed) _changes.add(_items);
  }

  void _scheduleRetry() {
    _timer?.cancel();
    _timer = null;
    if (!_active || retryAfter == Duration.zero) return;
    final waiting = _items.any((i) => i.step != UploadStep.failed);
    if (waiting) _timer = Timer(retryAfter, drain);
  }

  void dispose() {
    _disposed = true;
    _timer?.cancel();
    _onlineSub?.cancel();
    _changes.close();
    _uploaded.close();
  }
}
