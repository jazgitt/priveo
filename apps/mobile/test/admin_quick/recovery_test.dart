import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/core/ui/widgets.dart';
import 'package:priveo/features/admin_quick/actions/actions_screens.dart';
import 'package:priveo/features/admin_quick/actions/checklists_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';
import '../contract/contract_http.dart';
import 'operations_actions_test.dart' as operations;

Future<void> page(WidgetTester t,ContractHttp http,Widget screen)async{
  t.view.physicalSize=const Size(1200,2600);t.view.devicePixelRatio=1;addTearDown(t.view.reset);
  await t.pumpWidget(ProviderScope(retry:(_,_)=>null,overrides:[dioProvider.overrideWithValue(http.dio()),readRefreshProvider.overrideWith((_)=>const Stream<int>.empty())],child:MaterialApp(theme:adminTheme,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:screen)));
  await t.pumpAndSettle();
}
void main(){
  final screens=<String,Widget>{'Customers':const AdminCustomersScreen(),'Customer':const AdminCustomerScreen(id:'c1'),'Crew':const AdminCrewScreen(),'Addons':const AdminAddonsScreen(),'Checkins':const AdminCheckinsScreen(),'Checklists':const AdminChecklistsScreen(),'Operations':const AdminOperationsScreen()};
  for(final entry in screens.entries){
    testWidgets('admin ${entry.key} surfaces request errors and recovers without restarting',(t)async{
      final http=ContractHttp()..status=409;
      http.overrides.addAll({'/v1/admin/customers':<Object>[], '/v1/admin/customers/c1':{'first_name':'Asha','last_name':'Rao','email':'asha@example.test','mobile':'9000000001','flat':'A1','email_verified':true,'vehicles':<Object>[]},'/v1/admin/crew':<Object>[], '/v1/admin/addons':<Object>[], '/v1/admin/operations/jobs':<Object>[], '/v1/admin/operations/reasons':<Object>[], '/v1/admin/checkins':{'category_averages':{'Care':4.5},'items':[{'customer_name':'Asha','society':'Lake','vehicle_label':'HR01','cycle_start':'2026-10-20','answers':[{'category':'Care','rating':5}],'comment':'Excellent'}]}});
      await page(t,http,entry.value);expect(find.byType(ErrorView),findsWidgets);
      http.status=200;await t.tap(find.text('Try again').last);await t.pumpAndSettle();expect(find.byType(ErrorView),findsNothing);
      if(entry.key=='Customers'){await t.enterText(find.byType(TextField),'Asha');await t.pumpAndSettle();expect(http.requests.last.queryParameters['q'],'Asha');}
      if(entry.key=='Checkins'){expect(find.text('Care · 5'),findsOneWidget);expect(find.text('Excellent'),findsOneWidget);}
    });
  }
  testWidgets('customer date selection, pause and rejected skip remain reviewable',(t)async{
    final adapter=operations.Adapter();await operations.app(t,const AdminCustomerScreen(id:'c1'),adapter);
    await t.tap(find.textContaining('From date:').first);await t.pumpAndSettle();await t.tap(find.text('OK'));await t.pumpAndSettle();
    await t.tap(find.textContaining('To date:').first);await t.pumpAndSettle();await t.tap(find.text('OK'));await t.pumpAndSettle();
    await t.tap(find.text('Pause'));await t.pumpAndSettle();expect(adapter.writes.last.path,'/v1/admin/vehicles/v1/pauses');
    await t.tap(find.text('Un-skip'));await t.pumpAndSettle();expect(adapter.writes.last.method,'DELETE');
    adapter.reject=true;await t.tap(find.text('Skip date'));await t.pumpAndSettle();expect(find.text('The next-day retry date has passed.'),findsOneWidget);
  });
  testWidgets('late-start exception records chosen time and preserves form on failure',(t)async{
    final adapter=operations.Adapter();await operations.app(t,const AdminCrewScreen(),adapter);
    await t.tap(find.text('Add crew exception'));await t.pumpAndSettle();await t.tap(find.text('Sick'));await t.pumpAndSettle();await t.tap(find.text('Late start').last);await t.pumpAndSettle();
    await t.tap(find.textContaining('Start time:'));await t.pumpAndSettle();await t.tap(find.text('OK'));await t.pumpAndSettle();
    for(final label in ['From date:','To date:']){await t.tap(find.textContaining(label));await t.pumpAndSettle();await t.tap(find.text('OK'));await t.pumpAndSettle();}
    adapter.reject=true;await t.tap(find.text('Save'));await t.pumpAndSettle();expect(find.text('The next-day retry date has passed.'),findsOneWidget);
    adapter.reject=false;await t.tap(find.text('Save'));await t.pumpAndSettle();expect(adapter.writes.last.data['kind'],'Late start');expect(adapter.writes.last.data['start'],'08:00');expect(find.byType(AlertDialog),findsNothing);
  });
}
