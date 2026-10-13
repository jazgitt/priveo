import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/ui/widgets.dart';
import 'package:priveo/features/crew/crew_text.dart';
import 'package:priveo/features/crew/capture/media_capture.dart';
import 'package:priveo/features/crew/home/crew_home_screen.dart';
import 'package:priveo/features/crew/job/job_card_screen.dart';
import 'package:priveo/features/crew/job/perform_service_screen.dart';
import 'package:priveo/features/crew/job/could_not_complete_screen.dart';
import 'package:priveo/features/crew/profile/crew_profile_screen.dart';
import 'package:priveo/features/crew/manager/manager_schedule_screen.dart';
import 'package:priveo/features/crew/manager/manager_hours_screen.dart';
import 'package:priveo/features/crew/manager/manager_attendance_screen.dart';
import 'package:priveo/features/crew/notifications/crew_notifications.dart';
import 'package:priveo/features/crew/data/crew_models.dart';
import 'package:priveo/features/crew/data/manager_models.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/features/crew/manager/manager_job_screen.dart';
import '../contract/contract_http.dart';
import 'support.dart';

class RecoveryBackend extends FakeCrewBackend {
  RecoveryBackend():super(role:'Manager');
  @override
  Future<List<CrewReason>> reasons() async {
    if(offline) throw const ApiFailure();
    return super.reasons();
  }
}

void main(){
  final screens=<String,Widget>{'Home':const CrewHomeScreen(),'Job':const JobCardScreen(jobId:'j1'),'Manager job':const ManagerJobScreen(jobId:'j1'),'Perform':const PerformServiceScreen(jobId:'j1'),'Cannot complete':const CouldNotCompleteScreen(jobId:'j1'),'Profile':const CrewProfileScreen(),'Manager schedule':const ManagerScheduleScreen(),'Hours':const ManagerHoursScreen(),'Attendance':const ManagerAttendanceScreen()};
  for(final entry in screens.entries){
    testWidgets('${entry.key} explains offline failure and recovers on retry',(t)async{
      final backend=RecoveryBackend()..offline=true;
      await pumpCrew(t,entry.value,backend:backend);expect(find.byType(ErrorView),findsWidgets);
      backend.offline=false;await t.tap(find.text('Try again').first);await t.pumpAndSettle();expect(find.byType(ErrorView),findsNothing);
    });
  }
  test('crew inbox adapter reads dates and preserves mark-read failures',()async{
    final http=ContractHttp();final r=DioCrewInboxRepository(http.dio());
    expect((await r.inbox()).items,isNotEmpty);await r.markRead('n1');await r.markAllRead();expect(http.requests.last.path,'/v1/crew/notifications/read-all');
    http.status=409;await expectLater(r.inbox(),throwsA(isA<Exception>()));
  });
  testWidgets('crew profile uploads gallery photos and rejects the exact size limit',(t)async{
    final backend=FakeCrewBackend();final capture=FakeCapture();await pumpCrew(t,const CrewProfileScreen(),backend:backend,capture:capture);
    await t.tap(find.text(CrewText.choosePhoto));await t.pumpAndSettle();expect(capture.photos,1);expect(backend.sendCount,1);
    capture.next=const CapturedFile(path:'/large.jpg',contentType:'image/jpeg',sizeBytes:10*1024*1024,video:false);
    await t.tap(find.text(CrewText.takePhoto));await t.pumpAndSettle();expect(backend.sendCount,1);expect(find.textContaining('under 10 MB'),findsOneWidget);
    backend.offline=true;capture.next=const CapturedFile(path:'/valid.jpg',contentType:'image/jpeg',sizeBytes:100,video:false);
    await t.tap(find.text(CrewText.takePhoto));await t.pumpAndSettle();expect(find.byType(SnackBar),findsOneWidget);
  });
  testWidgets('manager hour editing supports time selection, cancellation and failed-save retry',(t)async{
    final backend=RecoveryBackend();
    final hours=CrewHours(crewId:'c1',name:'Raj',role:'Member',days:[const HoursDay(day:'Monday',working:true,start:'06:00',end:'12:00')]);
    await pumpCrew(t,Scaffold(body:Builder(builder:(c)=>TextButton(onPressed:()=>Navigator.of(c).push(MaterialPageRoute<void>(builder:(_)=>ManagerHoursEditScreen(hours:hours))),child:const Text('Edit')))),backend:backend);
    await t.tap(find.text('Edit'));await t.pumpAndSettle();await t.tap(find.text('06:00'));await t.pumpAndSettle();await t.tap(find.text('OK'));await t.pumpAndSettle();
    await t.tap(find.text('12:00'));await t.pumpAndSettle();await t.tap(find.text('Cancel'));await t.pumpAndSettle();
    await t.tap(find.byType(SwitchListTile));await t.pumpAndSettle();await t.tap(find.byType(SwitchListTile));await t.pumpAndSettle();
    backend.offline=true;await t.tap(find.text(CrewText.save));await t.pumpAndSettle();expect(find.byType(SnackBar),findsOneWidget);
    backend.offline=false;await t.tap(find.text(CrewText.save));await t.pumpAndSettle();expect(find.text('Edit'),findsOneWidget);
  });
  testWidgets('perform service keeps checklist and completion available after a failed request',(t)async{
    final backend=RecoveryBackend();backend.jobs['j1']!.status='In progress';
    await pumpCrew(t,const PerformServiceScreen(jobId:'j1'),backend:backend);
    backend.offline=true;await t.tap(find.text('Item a'));await t.pumpAndSettle();expect(find.byType(SnackBar),findsOneWidget);
    backend.offline=false;await t.tap(find.text('Item a'));await t.pumpAndSettle();await t.tap(find.text('Item b'));await t.pumpAndSettle();
    await t.tap(find.text(CrewText.takePhoto));await t.pumpAndSettle();backend.offline=true;
    await t.tap(find.text(CrewText.markComplete));await t.pumpAndSettle();expect(find.byType(PerformServiceScreen),findsOneWidget);expect(find.byType(SnackBar),findsOneWidget);
  });
  testWidgets('manager could-not-complete attaches proof and retains the form on failed submit',(t)async{
    final backend=RecoveryBackend();final capture=FakeCapture();
    await pumpCrew(t,Scaffold(body:Builder(builder:(c)=>TextButton(onPressed:()=>Navigator.of(c).push(MaterialPageRoute<void>(builder:(_)=>const CouldNotCompleteScreen(jobId:'j1',manager:true))),child:const Text('Open')))),backend:backend,capture:capture);
    await t.tap(find.text('Open'));await t.pumpAndSettle();await t.tap(find.text('Other'));await t.pumpAndSettle();
    capture.next=const CapturedFile(path:'/bad.pdf',contentType:null,sizeBytes:10,video:false);await t.tap(find.text(CrewText.addPhoto));await t.pumpAndSettle();expect(find.text(CrewText.formatNotAccepted),findsOneWidget);
    capture.next=const CapturedFile(path:'/good.jpg',contentType:'image/jpeg',sizeBytes:100,video:false);await t.tap(find.text(CrewText.addPhoto));await t.pumpAndSettle();expect(find.text(CrewText.photoAttached),findsOneWidget);
    backend.offline=true;await t.tap(find.text(CrewText.confirm));await t.pumpAndSettle();expect(find.byType(CouldNotCompleteScreen),findsOneWidget);
    backend.offline=false;await t.tap(find.text(CrewText.confirm));await t.pumpAndSettle();expect(find.text('Open'),findsOneWidget);expect(backend.couldNot['j1']?['upload'],isNotNull);
  });
  testWidgets('manager skip cancellation changes nothing and a failed skip remains actionable',(t)async{
    final backend=RecoveryBackend();await pumpCrew(t,const ManagerJobScreen(jobId:'j1'),backend:backend);
    await t.tap(find.text(CrewText.skipJob));await t.pumpAndSettle();await t.tap(find.text(CrewText.cancel));await t.pumpAndSettle();expect(backend.skipped,isEmpty);
    backend.offline=true;await t.tap(find.text(CrewText.skipJob));await t.pumpAndSettle();await t.tap(find.text(CrewText.skipJob).last);await t.pumpAndSettle();expect(backend.skipped,isEmpty);expect(find.byType(SnackBar),findsOneWidget);
  });
}
