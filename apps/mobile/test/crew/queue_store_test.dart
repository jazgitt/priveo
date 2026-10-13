import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/features/crew/upload/sqlite_store.dart';
import 'package:priveo/features/crew/upload/upload_queue.dart';
import 'package:sqflite/sqflite.dart';

/// Persistent database fake shared by reopened adapters. Native SQLite schema
/// upgrades and filesystem persistence are separate device scenarios.
class _Database implements Database {
  final rows = <int, Map<String, Object?>>{};
  int next = 1;

  @override
  Future<int> insert(String table, Map<String, Object?> values,
      {String? nullColumnHack, ConflictAlgorithm? conflictAlgorithm}) async {
    final id = next++;
    rows[id] = {...values, 'id': id};
    return id;
  }

  @override
  Future<List<Map<String, Object?>>> query(String table,
      {bool? distinct, List<String>? columns, String? where, List<Object?>? whereArgs,
      String? groupBy, String? having, String? orderBy, int? limit, int? offset}) async {
    if (where != 'owner_login_id = ?') throw StateError('Unscoped read');
    return rows.values.where((r) => r['owner_login_id'] == whereArgs!.single)
        .map((r) => Map<String, Object?>.of(r)).toList();
  }

  @override
  Future<int> update(String table, Map<String, Object?> values,
      {String? where, List<Object?>? whereArgs, ConflictAlgorithm? conflictAlgorithm}) async {
    if (where != 'id = ? AND owner_login_id = ?') throw StateError('Unscoped write');
    final id = whereArgs!.first as int;
    if (rows[id]?['owner_login_id'] != whereArgs.last) return 0;
    rows[id] = Map<String, Object?>.of(values);
    return 1;
  }

  @override
  Future<int> delete(String table, {String? where, List<Object?>? whereArgs}) async {
    if (where != 'id = ? AND owner_login_id = ?') throw StateError('Unscoped delete');
    final id = whereArgs!.first as int;
    if (rows[id]?['owner_login_id'] != whereArgs.last) return 0;
    rows.remove(id);
    return 1;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

QueuedUpload draft(String? owner) => QueuedUpload(id: 0, ownerId: owner,
    jobId: 'job', kind: 'photo', stage: 'After', path: '/kept/photo.jpg',
    contentType: 'image/jpeg', sizeBytes: 100);

void main() {
  test('reopened queue adapters retain only their own uploads and quarantine legacy rows', () async {
    final database = _Database();
    final a = SqliteUploadQueueStore(ownerId: 'a', database: database);
    final b = SqliteUploadQueueStore(ownerId: 'b', database: database);
    final original = await a.add(draft('a'));
    final other = await b.add(draft('b'));
    await database.insert('upload_queue', draft(null).toRow()..remove('id'));
    await a.update(original.copyWith(step: UploadStep.failed, lastError: 'Offline'));
    final reopened = SqliteUploadQueueStore(ownerId: 'a', database: database);
    expect((await reopened.all()).single.step, UploadStep.failed);
    expect((await b.all()).single.id, other.id);
    await b.remove(original.id);
    expect((await reopened.all()).single.id, original.id);
    await expectLater(b.update(original), throwsStateError);
    await expectLater(b.add(draft('a')), throwsStateError);
    await a.remove(original.id);
    expect(await reopened.all(), isEmpty);
    expect(database.rows.length, 2); // Other owner's file and unknown legacy file.
  });

  test('queue identity is stable across token refresh and distinct across logins', () {
    Session session(String id, int expiry) {
      final payload = base64Url.encode(utf8.encode(jsonEncode({'sub': id, 'exp': expiry})));
      return Session(role: Role.crew, displayName: 'Crew', accessToken: 'header.$payload.signature',
          refreshToken: 'refresh');
    }
    const a = '11111111-1111-1111-1111-111111111111';
    const b = '22222222-2222-2222-2222-222222222222';
    expect(session(a, 1).loginId, session(a, 2).loginId);
    expect(session(a, 1).loginId, isNot(session(b, 1).loginId));
    expect(const Session(role: Role.crew, displayName: 'Crew', accessToken: 'bad',
        refreshToken: 'bad').loginId, isNull);
  });
}
