import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/features/crew/data/crew_models.dart';
import 'package:priveo/features/crew/data/crew_repository.dart';
import 'package:priveo/features/crew/upload/upload_queue.dart';

class _Api implements UploadApi {
  final calls = <String>[];
  Object? failRequest;
  Object? failSend;
  Object? failConfirm;
  Completer<void>? requestGate;
  int _n = 0;

  @override
  Future<UploadTicket> requestUpload({
    required String purpose,
    String? jobId,
    required String kind,
    String? stage,
    required String contentType,
    required int sizeBytes,
  }) async {
    if (failRequest != null) throw failRequest!;
    final id = 'u${++_n}';
    calls.add('request $id');
    if (requestGate != null) await requestGate!.future;
    return UploadTicket(
        id: id, url: '/media/$id', method: 'PUT', headers: const {'a': 'b'});
  }

  @override
  Future<void> sendFile(UploadTicket ticket, String path) async {
    if (failSend != null) throw failSend!;
    calls.add('send ${ticket.id}');
  }

  @override
  Future<void> confirm(String uploadId) async {
    if (failConfirm != null) throw failConfirm!;
    calls.add('confirm $uploadId');
  }
}

Future<QueuedUpload> _add(UploadQueue q, {String job = 'j1'}) => q.enqueue(
    jobId: job,
    kind: 'photo',
    stage: 'Before',
    path: '/tmp/a.jpg',
    contentType: 'image/jpeg',
    sizeBytes: 100);

Future<void> _settle() => Future<void>.delayed(Duration.zero);

class UnavailableStore extends MemoryUploadQueueStore {
  @override Future<List<QueuedUpload>> all() async => throw StateError('Storage unavailable');
}

void main() {
  late _Api api;
  late MemoryUploadQueueStore store;

  UploadQueue make({Stream<bool>? online}) => UploadQueue(
      api: api, store: store, online: online, retryAfter: Duration.zero);

  setUp(() {
    api = _Api();
    store = MemoryUploadQueueStore();
  });

  test('unavailable local storage does not prevent opening an empty queue',()async{
    final q=UploadQueue(api:api,store:UnavailableStore(),retryAfter:Duration.zero);addTearDown(q.dispose);
    await q.start();expect(q.items,isEmpty);expect(api.calls,isEmpty);
  });
  test('a file read failure is parked and can be retried after repair',()async{
    final q=make();addTearDown(q.dispose);api.failSend=StateError('Cannot read file');
    final item=await _add(q);await _settle();expect(q.items.single.step,UploadStep.failed);expect(q.items.single.lastError,contains('Cannot read file'));
    api.failSend=null;await q.retry(item.id);await _settle();expect(q.items,isEmpty);await q.retry(999);expect(await store.all(),isEmpty);
  });
  test('retry timer resumes an offline upload without another user action',()async{
    final q=UploadQueue(api:api,store:store,retryAfter:const Duration(milliseconds:20));addTearDown(q.dispose);
    api.failRequest=const ApiFailure();await _add(q);await _settle();expect(q.items,hasLength(1));
    api.failRequest=null;await Future<void>.delayed(const Duration(milliseconds:50));expect(q.items,isEmpty);expect(api.calls.last,'confirm u1');
  });
  test('account change during file stashing discards the copy and queues nothing',()async{
    var active=true;final discarded=<String>[];
    final q=UploadQueue(api:api,store:store,ownerId:'owner-a',isCurrent:()=>active,retryAfter:Duration.zero,stash:(path)async{active=false;return '/kept/photo.jpg';},discard:(path)async{discarded.add(path);});addTearDown(q.dispose);
    await expectLater(_add(q),throwsA(isA<ApiFailure>().having((e)=>e.code,'code','signed_out')));
    expect(discarded,['/kept/photo.jpg']);expect(await store.all(),isEmpty);expect(api.calls,isEmpty);
  });

  test('account queues ignore other owners and unknown legacy records', () async {
    for (final owner in ['owner-a', 'owner-b', null]) {
      await store.add(QueuedUpload(id: 0, jobId: 'job-$owner', kind: 'photo',
          stage: 'After', path: '/photo.jpg', contentType: 'image/jpeg',
          sizeBytes: 100, ownerId: owner));
    }
    final q = UploadQueue(api: api, store: store, ownerId: 'owner-b',
        retryAfter: Duration.zero);
    addTearDown(q.dispose);
    await q.start();
    final remaining = await store.all();
    expect(remaining.map((i) => i.ownerId), ['owner-a', null]);
    expect(api.calls, ['request u1', 'send u1', 'confirm u1']);
  });

  test('account switch stops after in-flight request and resumes for original owner', () async {
    var current = 'owner-a';
    api.requestGate = Completer<void>();
    final q = UploadQueue(api: api, store: store, ownerId: 'owner-a',
        isCurrent: () => current == 'owner-a', retryAfter: Duration.zero);
    addTearDown(q.dispose);
    await _add(q);
    await _settle();
    current = 'owner-b';
    api.requestGate!.complete();
    await _settle();
    expect(api.calls, ['request u1']);
    expect((await store.all()).single.ownerId, 'owner-a');
    expect((await store.all()).single.step, UploadStep.requested);
    await q.drain();
    expect(api.calls, ['request u1']);
    api.requestGate = null;
    final resumed = UploadQueue(api: api, store: store, ownerId: 'owner-a',
        retryAfter: Duration.zero);
    addTearDown(resumed.dispose);
    await resumed.start();
    expect(api.calls, ['request u1', 'send u1', 'confirm u1']);
    expect(await store.all(), isEmpty);
  });

  test('signed-out immediate upload cannot reach the API', () async {
    final q = UploadQueue(api: api, store: store, ownerId: 'owner-a',
        isCurrent: () => false, retryAfter: Duration.zero);
    addTearDown(q.dispose);
    await expectLater(q.sendNow(purpose: 'profile', kind: 'photo', path: '/photo.jpg',
        contentType: 'image/jpeg', sizeBytes: 100), throwsA(isA<ApiFailure>()));
    expect(api.calls, isEmpty);
  });

  test('a queued file is requested, sent and confirmed, then removed',
      () async {
    final discarded = <String>[];
    final q = UploadQueue(
        api: api,
        store: store,
        retryAfter: Duration.zero,
        discard: (p) async => discarded.add(p));
    final uploaded = <String>[];
    q.uploaded.listen(uploaded.add);

    await _add(q);
    await _settle();
    await q.drain();
    await _settle();

    expect(api.calls, ['request u1', 'send u1', 'confirm u1']);
    expect(q.items, isEmpty);
    expect(await store.all(), isEmpty);
    expect(uploaded, ['j1']);
    expect(discarded, ['/tmp/a.jpg']);
  });

  test('with no connection the file stays and goes out when it returns',
      () async {
    final online = StreamController<bool>();
    final q = make(online: online.stream);
    await q.start();
    api.failRequest = const ApiFailure();

    await _add(q);
    await _settle();
    expect(q.items, hasLength(1));
    expect(q.items.single.step, UploadStep.queued);
    expect(q.items.single.attempts, 0);

    api.failRequest = null;
    online.add(true);
    await _settle();
    await _settle();
    expect(q.items, isEmpty);
    expect(api.calls.last, startsWith('confirm'));
    await online.close();
  });

  test('after the app closes, the queue resumes at the saved step', () async {
    // The file was requested and sent before the app closed.
    final saved = await store.add(const QueuedUpload(
        id: 0,
        jobId: 'j1',
        kind: 'photo',
        stage: 'Before',
        path: '/tmp/a.jpg',
        contentType: 'image/jpeg',
        sizeBytes: 100));
    await store.update(saved.copyWith(
        step: UploadStep.sent,
        uploadId: 'u9',
        ticket: const UploadTicket(
            id: 'u9', url: '/media/u9', method: 'PUT', headers: {})));

    final q = make();
    await q.start();

    expect(api.calls, ['confirm u9']);
    expect(q.items, isEmpty);
  });

  test('a file that was requested but not sent is sent on resume without a '
      'new request', () async {
    final saved = await store.add(const QueuedUpload(
        id: 0,
        jobId: 'j1',
        kind: 'video',
        stage: 'During',
        path: '/tmp/a.mp4',
        contentType: 'video/mp4',
        sizeBytes: 100));
    await store.update(saved.copyWith(
        step: UploadStep.requested,
        uploadId: 'u5',
        ticket: const UploadTicket(
            id: 'u5', url: '/media/u5', method: 'PUT', headers: {})));

    await make().start();
    expect(api.calls, ['send u5', 'confirm u5']);
  });

  test('an expired link (403) asks for a new one', () async {
    final q = make();
    api.failSend =
        const ApiFailure(code: 'forbidden', message: 'x', statusCode: 403);
    await _add(q);
    await _settle();
    await q.drain();
    expect(q.items.single.step, UploadStep.queued);
    expect(q.items.single.ticket, isNull);

    api.failSend = null;
    await q.drain();
    expect(q.items, isEmpty);
    expect(api.calls.last, startsWith('confirm'));
    expect(api.calls.where((c) => c.startsWith('request')).length, greaterThan(1));
  });

  test('a link the storage no longer knows (404 before sending) asks for a new one',
      () async {
    final q = make();
    api.failSend =
        const ApiFailure(code: 'not_found', message: 'x', statusCode: 404);
    await _add(q);
    await _settle();
    await q.drain();
    expect(q.items.single.step, UploadStep.queued);
    expect(q.items.single.ticket, isNull);

    api.failSend = null;
    await q.drain();
    expect(q.items, isEmpty);
  });

  test('a file the host refuses as too large (413) is parked, not retried forever',
      () async {
    final q = make();
    // What ApiFailure.fromDio makes of a 413 page without our error envelope.
    api.failSend = const ApiFailure(
        code: 'too_large', message: 'This file is too large to send.', statusCode: 413);
    await _add(q);
    await _settle();
    expect(q.items.single.step, UploadStep.failed);
    expect(q.items.single.lastError, 'This file is too large to send.');
    final sends = api.calls.length;
    await q.drain();
    expect(api.calls.length, sends, reason: 'a failed file waits for Retry or Remove');
  });

  test('remove takes a file off the phone for good', () async {
    final discarded = <String>[];
    final q = UploadQueue(api: api, store: store, retryAfter: Duration.zero,
        discard: (path) async => discarded.add(path));
    addTearDown(q.dispose);
    api.failRequest = const ApiFailure(
        code: 'validation_failed', message: 'Too big', statusCode: 422);
    final item = await _add(q);
    await _settle();
    await q.remove(item.id);
    expect(q.items, isEmpty);
    expect(await store.all(), isEmpty);
    expect(discarded, ['/tmp/a.jpg']);
    await q.remove(999); // nothing to remove: no error
  });

  test('a rejected file is parked as failed, and retry puts it back',
      () async {
    final q = make();
    api.failRequest = const ApiFailure(
        code: 'validation_failed', message: 'Too big', statusCode: 422);
    await _add(q);
    await _settle();
    expect(q.items.single.step, UploadStep.failed);
    expect(q.items.single.lastError, 'Too big');

    api.failRequest = null;
    await q.retry(q.items.single.id);
    await _settle();
    await q.drain();
    expect(q.items, isEmpty);
  });

  test('repeated server errors park the file after the attempt limit',
      () async {
    final q = UploadQueue(
        api: api, store: store, retryAfter: Duration.zero, maxAttempts: 3);
    api.failRequest =
        const ApiFailure(code: 'error', message: 'oops', statusCode: 500);
    await _add(q);
    await _settle();
    await q.drain();
    await q.drain();
    expect(q.items.single.step, UploadStep.failed);
    expect(q.items.single.attempts, 3);
  });

  test('waitingFor counts the files of one job', () async {
    final q = make();
    api.failRequest = const ApiFailure();
    await _add(q);
    await _add(q);
    await _add(q, job: 'j2');
    await _settle();
    expect(q.waitingFor('j1'), 2);
    expect(q.waitingFor('j2'), 1);
  });

  test('queued rows round trip through the database mapping', () {
    const item = QueuedUpload(
      id: 4,
      jobId: 'j1',
      kind: 'video',
      stage: 'After',
      path: '/x/y.mp4',
      contentType: 'video/mp4',
      sizeBytes: 999,
      uploadId: 'u1',
      ticket: UploadTicket(
          id: 'u1',
          url: '/media/u1',
          method: 'PUT',
          headers: {'Content-Type': 'video/mp4'}),
      step: UploadStep.requested,
      attempts: 2,
      lastError: 'oops',
      ownerId: 'owner-a',
    );
    final back = QueuedUpload.fromRow(item.toRow());
    expect(back.id, 4);
    expect(back.step, UploadStep.requested);
    expect(back.ticket!.headers, {'Content-Type': 'video/mp4'});
    expect(back.attempts, 2);
    expect(back.lastError, 'oops');
    expect(back.ownerId, 'owner-a');
  });
}
