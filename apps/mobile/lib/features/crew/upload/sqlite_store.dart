import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import 'upload_queue.dart';

/// The queue on the phone's own database, so it survives the app closing.
class SqliteUploadQueueStore implements UploadQueueStore {
  Database? _db;

  Future<Database> _open() async => _db ??= await openDatabase(
        p.join(await getDatabasesPath(), 'priveo_uploads.db'),
        version: 1,
        onCreate: (db, _) => db.execute('''
          CREATE TABLE upload_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            stage TEXT NOT NULL,
            path TEXT NOT NULL,
            content_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            upload_id TEXT,
            upload_url TEXT,
            method TEXT,
            headers TEXT,
            step TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT
          )'''),
      );

  @override
  Future<List<QueuedUpload>> all() async {
    final db = await _open();
    final rows = await db.query('upload_queue', orderBy: 'id');
    return rows.map(QueuedUpload.fromRow).toList();
  }

  @override
  Future<QueuedUpload> add(QueuedUpload draft) async {
    final db = await _open();
    final row = draft.toRow()..remove('id');
    final id = await db.insert('upload_queue', row);
    return QueuedUpload.fromRow({...draft.toRow(), 'id': id});
  }

  @override
  Future<void> update(QueuedUpload item) async {
    final db = await _open();
    await db.update('upload_queue', item.toRow(),
        where: 'id = ?', whereArgs: [item.id]);
  }

  @override
  Future<void> remove(int id) async {
    final db = await _open();
    await db.delete('upload_queue', where: 'id = ?', whereArgs: [id]);
  }
}

/// Copies a captured file into the app's own folder, because the camera's
/// cache can be cleared before the file is sent.
Future<String> stashFile(String path) async {
  final dir = Directory(
      p.join((await getApplicationDocumentsDirectory()).path, 'uploads'));
  await dir.create(recursive: true);
  final target = p.join(
      dir.path, '${DateTime.now().microsecondsSinceEpoch}${p.extension(path)}');
  await File(path).copy(target);
  return target;
}

/// Removes a file once it is confirmed.
Future<void> discardFile(String path) async {
  try {
    await File(path).delete();
  } on FileSystemException {
    // Already gone.
  }
}
