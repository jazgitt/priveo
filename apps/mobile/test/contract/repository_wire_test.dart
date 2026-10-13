import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/features/admin_quick/actions/actions_data.dart';
import 'package:priveo/features/admin_quick/alerts/alerts_data.dart';
import 'package:priveo/features/admin_quick/payments/admin_payments_data.dart';
import 'package:priveo/features/admin_quick/data/admin_quick_repository.dart';
import 'package:priveo/features/crew/data/crew_repository.dart';
import 'package:priveo/features/crew/data/manager_models.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/customer/data/proof_reads_repository.dart';
import 'package:priveo/features/customer/calendar/calendar_actions.dart';
import 'package:priveo/features/customer/settings/notification_prefs_repository.dart';
import 'package:priveo/features/customer/account/account_data.dart';
import 'package:priveo/features/changes_money/data/money_repository.dart';
import 'package:priveo/features/support/data/support_repository.dart';
import 'package:priveo/features/auth/data/auth_repository.dart';
import 'package:priveo/core/api/api.g.dart' as wire;
import 'package:priveo/features/crew/capture/media_capture.dart';
import 'contract_http.dart';

void main() {
  final day=DateTime(2026,10,20);
  late ContractHttp http;
  setUp(()=>http=ContractHttp());
  test('authentication repository exchanges credentials and tolerates logout network failure',()async{
    final r=ApiAuthRepository(wire.PriveoApi(http.dio()));await r.start('customer@example.test');expect(await r.sendCode('customer@example.test'),isA<int>());expect(await r.verifyCode('customer@example.test','246810'),isNotEmpty);
    expect((await r.setPassword('token','Password12')).accessToken,isNotEmpty);expect((await r.login('customer@example.test','Password12')).refreshToken,isNotEmpty);await r.refresh('refresh');await r.logoutAll();
    http.status=409;await r.logout();await expectLater(r.logoutAll(),throwsA(isA<ApiFailure>()));
  });
  test('customer file upload sends bytes to a signed URL without API authentication',()async{
    http.overrides['/v1/customer/uploads']={'id':'u1','upload_url':'https://storage.unit.test/file','method':'PUT','headers':{'x-signed':'signed'}};
    http.overrides['/v1/customer/uploads/u1/confirm']={'id':'u1','url':'https://storage.unit.test/photo.jpg'};
    final r=DioAccountRepository(http.dio());final file=File('test/contract/account-upload.tmp');await file.writeAsBytes([1,2,3]);
    try{final upload=await r.upload(purpose:'vehicle',vehicleId:'v1',file:CapturedFile(path:file.path,contentType:'image/jpeg',sizeBytes:3,video:false));expect(upload.id,'u1');
      final signed=http.requests.singleWhere((r)=>r.path.startsWith('https://storage.'));expect(signed.extra['noAuth'],isTrue);expect(signed.headers['content-length'],3);
      http.status=409;await expectLater(r.upload(purpose:'vehicle',file:CapturedFile(path:file.path,contentType:'image/jpeg',sizeBytes:3,video:false)),throwsA(isA<ApiFailure>()));
    }finally{await file.delete();}
  });
  test('customer reads parse the API contract and preserve paging/filter parameters',()async{
    final r=DioCustomerReadsRepository(http.dio());
    expect((await r.calendar('2026-10',vehicleId:'v1')).month,'wire-value');
    expect(http.requests.last.queryParameters,{'month':'2026-10','vehicle_id':'v1'});
    await r.nextServices();final visit=await r.visit('v1');
    expect(visit.proof,isNotEmpty);
    await r.history(vehicleId:'v1',offset:30);expect(http.requests.last.queryParameters,{'offset':30,'vehicle_id':'v1'});
    expect(await r.vehicles(),isNotEmpty);expect((await r.vehicle('v1')).id,isNotEmpty);
    expect((await r.inbox()).items,isNotEmpty);await r.markRead('n1');await r.markAllRead();await r.registerDevice('token','android');
    expect(http.requests.last.data,{'token':'token','platform':'android'});
    final proof=DioProofReadsRepository(http.dio());
    expect(await proof.historyMonth('2026-10',vehicleId:'v1',offset:30),isNotEmpty);
    expect((await proof.historyMeta(vehicleId:'v1')).memberSince,isNotNull);expect(await proof.today(),isNotEmpty);
  });
  test('customer money sends dates, pricing actions and unique idempotency keys',()async{
    final r=DioMoneyRepository(http.dio());
    await r.changes('v1');expect(await r.upcoming('v1'),isNotEmpty);
    await r.skip('v1',day);expect(http.requests.last.data,{'date':'2026-10-20'});
    final key=http.requests.last.headers['Idempotency-Key'];expect(key,matches(RegExp(r'^[a-f0-9]{32}$')));
    await r.unskip('v1','s1');await r.pause('v1',day,day);expect(http.requests.last.headers['Idempotency-Key'],isNot(key));await r.endPause('v1','p1');
    await r.subscription('v1');expect(await r.payments('v1'),isNotEmpty);await r.paymentDetail('p1');await r.payNext('v1');await r.markPaid('p1');await r.invoice('p1');await r.addons();
    await r.requestAddon('v1',day,'12:00');expect(http.requests.last.data,{'service':'Deep Spa','date':'2026-10-20','finish_by':'12:00'});
    await r.requestStandalone(vehicleId:'v1',date:day,finishBy:'12:00',mobile:'9000000001',notes:'Gate 2');
    expect(http.requests.last.data,containsPair('vehicle_id','v1'));await r.cancelAddon('a1');
  });
  test('crew and manager adapters send attendance and job actions with their contract responses',()async{
    final r=ApiCrewRepository(http.dio());
    await r.visits(date:day);expect(http.requests.last.queryParameters,{'date':'2026-10-20'});await r.visits(all:true);expect(http.requests.last.queryParameters,{'all':true});
    await r.job('j1');await r.start('j1');await r.setChecked('j1','i1',true);expect(http.requests.last.data,{'checked':true});await r.complete('j1');
    await r.couldNotComplete('j1',reasonKey:'locked',note:'Gate',uploadId:'u1');expect(http.requests.last.data,{'reason_key':'locked','note':'Gate','upload_id':'u1'});
    expect(await r.reasons(),isNotEmpty);await r.profile();await r.setProfilePhoto('u1');await r.managerSchedule(day);expect(await r.managerCrew(),isNotEmpty);
    await r.managerJob('j1');await r.managerCouldNotComplete('j1',reasonKey:'locked');await r.managerSkip('j1');await r.managerReassign('j1','c2');expect(http.requests.last.data,{'crew_id':'c2'});
    await r.managerAttendance(day);await r.managerSetAttendance('c2',status:'Late start',from:day,to:day,start:'08:00');
    expect(http.requests.last.data,{'status':'Late start','from_date':'2026-10-20','to_date':'2026-10-20','start':'08:00'});
    expect(await r.managerHours(),isNotEmpty);await r.managerSetHours('c2',[HoursDay(day:'Monday',working:true,start:'06:00',end:'12:00')]);
    expect(await r.managerReassignOptions('j1'),isNotEmpty);
    final ticket=await r.requestUpload(purpose:'proof',jobId:'j1',kind:'photo',stage:'After',contentType:'image/jpeg',sizeBytes:5);
    final file=File('test/contract/upload-unit.tmp');await file.writeAsBytes([1,2,3,4,5]);
    try{await r.sendFile(ticket,file.path);expect(http.requests.last.extra['noAuth'],isTrue);expect(http.requests.last.headers['content-length'],5);await r.confirm(ticket.id);}finally{await file.delete();}
  });
  test('admin adapters decode home, complaints, feedback, schedule, payments and alerts',()async{
    final r=ApiAdminQuickRepository(http.dio());
    expect((await r.home()).paymentsToConfirm,isNotEmpty);await r.complaints(status:'Open',category:'Cleaning');expect(http.requests.last.queryParameters,{'status':'Open','category':'Cleaning'});
    await r.complaint('c1');await r.setStatus('c1','Resolved','Fixed');expect(http.requests.last.data,{'status':'Resolved','note':'Fixed'});await r.addNote('c1','Progress');
    await r.feedback(rating:5);await r.ratings();await r.needsScheduling(societyId:'s1');await r.day(day,societyId:'s1');await r.capacity('s1',day,days:14);expect(http.requests.last.queryParameters['days'],14);
    final p=DioAdminPaymentsRepository(http.dio());expect(await p.toConfirm(),isNotEmpty);await p.confirm('p1');await p.reject('p1');expect(await p.alerts(),isNotEmpty);await p.markRead('a1');
    final alerts=ApiAlertsRepository(http.dio());expect((await alerts.list()).items,isNotEmpty);await alerts.markRead('a1');await alerts.markAllRead();
    http.overrides['/v1/admin/customers']=[{'id':'c1'}];http.overrides['/v1/admin/customers/c1']={'id':'c1'};
    final actions=AdminActionsRepository(http.dio());await actions.list('/v1/admin/customers',{'q':'Asha'});await actions.detail('/v1/admin/customers/c1');await actions.post('/v1/admin/customers/c1/sessions/logout',{});await actions.remove('/v1/admin/vehicles/v1/skips/s1');
  });
  test('support adapters preserve feedback, complaint and check-in wire fields',()async{
    final r=ApiSupportRepository(http.dio());await r.contact();await r.options();
    await r.createComplaint(category:'Cleaning',description:'Missed',visitId:'v1',photoKeys:['u1']);expect(http.requests.last.data,containsPair('photo_keys',['u1']));
    expect(await r.complaints(),isNotEmpty);await r.complaint('c1');await r.reply('c1','Thank you');expect(http.requests.last.data,{'note':'Thank you'});
    await r.sendFeedback(category:'Service',rating:5,comment:'Great',testimonial:true);
    expect(http.requests.last.data,containsPair('testimonial_permission',true));await r.rateVisit('v1',rating:4,tags:['Care'],comment:'Good');
    expect(await r.pendingCheckIns(),isNotEmpty);await r.submitCheckIn('k1',{'Service':5},'Good');
    expect(http.requests.last.data,{'subscription_id':'k1','answers':[{'category':'Service','rating':5}],'comment':'Good'});
  });
  test('account, calendar and preference changes preserve optional fields',()async{
    final r=DioAccountRepository(http.dio());await r.profile();await r.editProfile(firstName:'Asha',lastName:'Rao',mobile:'9000000001');
    expect(http.requests.last.data,{'first_name':'Asha','last_name':'Rao','mobile':'9000000001'});await r.startEmailChange('new@example.test');await r.verifyEmail('246810');await r.changePassword(current:'old',next:'New123!');
    await r.vehicleAccount('v1');await r.editParking('v1',basement:'B2',number:'14');expect(http.requests.last.data,{'parking_basement':'B2','parking_number':'14'});
    final calendar=DioCalendarActions(http.dio());await calendar.skip('v1',day);await calendar.unskip('v1','s1');await calendar.changeCutoff('v1',day,'08:00');await calendar.updatePreferences('v1',cutoffTime:'08:00',interiorDay:'Friday');
    final prefs=DioNotificationPrefsRepository(http.dio());expect(await prefs.load(),isNotEmpty);await prefs.set('service_completed',false);
    expect(http.requests.last.data,{'items':[{'event':'service_completed','enabled':false}]});
  });
  test('all adapters preserve backend error codes and user-facing messages',()async{
    http.status=409;final dio=http.dio();
    final requests=<Future<dynamic> Function()>[
      ()=>DioCustomerReadsRepository(dio).vehicles(),()=>DioProofReadsRepository(dio).today(),()=>DioMoneyRepository(dio).addons(),()=>ApiCrewRepository(dio).job('j1'),()=>ApiAdminQuickRepository(dio).home(),()=>DioAdminPaymentsRepository(dio).confirm('p1'),()=>ApiAlertsRepository(dio).markAllRead(),()=>AdminActionsRepository(dio).post('/v1/admin/test',{}),()=>ApiSupportRepository(dio).contact(),()=>DioAccountRepository(dio).profile(),()=>DioAccountRepository(dio).changePassword(current:'old',next:'new'),()=>DioCalendarActions(dio).skip('v1',day),()=>DioNotificationPrefsRepository(dio).load(),()=>DioNotificationPrefsRepository(dio).set('service_completed',true),
    ];
    for(final send in requests){await expectLater(send(),throwsA(isA<ApiFailure>().having((e)=>e.code,'code','conflict').having((e)=>e.message,'message','Please review the change.').having((e)=>e.statusCode,'status',409)));}
  });
}
