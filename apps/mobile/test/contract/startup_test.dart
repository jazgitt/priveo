import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/config/app_config.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/main_test.dart' as test_entry;
import 'package:priveo/main.dart' as prod;
import 'package:priveo/features/crew/routes.dart' as crew;
import 'package:priveo/features/scheduling/dto.dart';
void main(){
    testWidgets('both entry points select their flavor and open signed-out welcome',(t)async{
      for(final production in [false,true]){
      const channel=MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
      t.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel,(_)async=>null);
      addTearDown(()=>t.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel,null));
      if(production){prod.main();}else{test_entry.main();}
      await t.pump();await t.pump(const Duration(seconds:3));await t.pumpAndSettle();
      final container=ProviderScope.containerOf(t.element(find.byType(MaterialApp)));
      expect(container.read(appConfigProvider),production?AppConfig.prod:AppConfig.test);expect(find.text('Get started'),findsOneWidget);
      await t.pumpWidget(const SizedBox());await t.pump();
      }
    });
  test('legacy scheduling DTOs preserve empty assignments and private crew details',(){
    expect(nextServiceFromJson({'job':null}),isNull);
    final job=nextServiceFromJson({'job':<String,dynamic>{'job_id':'j1','visit_id':'v1','vehicle_id':'car1','registration':'HR01','vehicle':'Creta','date':'2026-10-20','service':'Deep Spa','status':'Scheduled','start_time':'07:00','end_time':'09:00','crew_name':'Raj','finish_by':'12:00'}})!;
    expect(job.date,DateTime(2026,10,20));expect(job.crewName,'Raj');
    final day=CrewDay.fromJson({'date':'2026-10-20','society':'Lake','total':1,'done':0,'left':1,'jobs':[<String,dynamic>{'id':'j1','visit_id':'v1','vehicle_id':'car1','registration':'HR01','make':'Hyundai','model':'Creta','category':'SUV','parking_basement':'B2','parking_number':'14','society':'Lake','service':'Deep Spa','status':'Scheduled'}]});
    expect(day.jobs.single.parkingNumber,'14');expect(day.left,1);expect(crew.routes,isNotEmpty);
  });
}
