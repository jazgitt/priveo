import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:sqflite/sqflite.dart';
import 'package:priveo/features/crew/upload/sqlite_store.dart';

class Factory extends Mock implements DatabaseFactory {}
class Db extends Mock implements Database {}
void main(){
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(()=>registerFallbackValue(OpenDatabaseOptions()));
  test('queue creation and v1 upgrade add nullable owner identity and scoped reads',()async{
    final factory=Factory();final db=Db();final sql=<String>[];
    when(()=>factory.getDatabasesPath()).thenAnswer((_)async=>'test/crew');
    when(()=>db.execute(any())).thenAnswer((i)async{sql.add(i.positionalArguments.first as String);});
    when(()=>db.query('upload_queue',where:'owner_login_id = ?',whereArgs:['owner-a'],orderBy:'id')).thenAnswer((_)async=>[]);
    when(()=>factory.openDatabase(any(),options:any(named:'options'))).thenAnswer((i)async{
      final options=i.namedArguments[#options] as OpenDatabaseOptions;expect(options.version,2);
      await options.onCreate!(db,2);await options.onUpgrade!(db,1,2);
      final count=sql.length;await options.onUpgrade!(db,2,2);expect(sql.length,count);return db;
    });
    final store=SqliteUploadQueueStore(ownerId:'owner-a',factory:factory);expect(await store.all(),isEmpty);expect(await store.all(),isEmpty);
      expect(sql.any((s)=>s.contains('CREATE TABLE') && s.contains('owner_login_id TEXT')),isTrue);
      expect(sql.any((s)=>s.contains('ALTER TABLE upload_queue ADD COLUMN owner_login_id TEXT')),isTrue);
      verify(()=>factory.openDatabase(any(),options:any(named:'options'))).called(1);
  });
}
