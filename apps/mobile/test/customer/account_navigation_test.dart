import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/features/customer/account/account_sections.dart';
import 'package:priveo/features/customer/account/account_data.dart';
import 'package:priveo/features/customer/account/account_strings.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/changes_money/data/money_repository.dart';
import 'package:priveo/l10n/app_localizations.dart';
import '../changes_money/fakes.dart';
import 'account_test.dart' show FakeAccount;

Future<GoRouter> show(WidgetTester t,int count)async{
  t.view.physicalSize=const Size(1000,2800);t.view.devicePixelRatio=2;addTearDown(t.view.reset);
  final router=GoRouter(initialLocation:'/customer',routes:[
    GoRoute(path:'/customer',builder:(_,_)=>const Scaffold(body:SingleChildScrollView(child:Column(children:[AccountProfileHeader(),AccountSubscriptionCards(),AccountMoreLinks()])))),
    for(final path in ['/customer/vehicles/:vehicleId/addons','/customer/vehicles/:vehicleId/skip-pause','/customer/vehicles/:vehicleId/subscription','/customer/support','/customer/support/complaints'])
      GoRoute(path:path,builder:(_,s)=>Scaffold(appBar:AppBar(),body:Text('Destination ${s.uri.path}'))),
  ]);addTearDown(router.dispose);
  await t.pumpWidget(ProviderScope(retry:(_,_)=>null,overrides:[
    readRefreshProvider.overrideWith((_)=>const Stream<int>.empty()),accountRepositoryProvider.overrideWithValue(FakeAccount()),moneyRepositoryProvider.overrideWithValue(FakeMoneyRepository()),
    accountVehiclesProvider.overrideWith((_)async=>List.generate(count,(i)=>VehicleSummaryDto(id:'v${i+1}',registration:'HR0$i',model:i==0?'Creta':'Swift',society:'Lake',subscriptionStatus:'Active'))),
  ],child:MaterialApp.router(routerConfig:router,theme:customerTheme,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales)));
  await t.pumpAndSettle();return router;
}
void main(){
  testWidgets('account vehicle menus select the intended vehicle and preserve navigation',(t)async{
    final router=await show(t,2);
    await t.tap(find.text(AccountStrings.menuAddons));await t.pumpAndSettle();expect(find.text(AccountStrings.chooseVehicle),findsOneWidget);await t.tap(find.text('Swift'));await t.pumpAndSettle();expect(find.text('Destination /customer/vehicles/v2/addons'),findsOneWidget);
    router.pop();await t.pumpAndSettle();await t.tap(find.text(AccountStrings.menuSkipPause));await t.pumpAndSettle();await t.tap(find.text('Creta'));await t.pumpAndSettle();expect(find.text('Destination /customer/vehicles/v1/skip-pause'),findsOneWidget);
    router.pop();await t.pumpAndSettle();await t.tap(find.text(AccountStrings.menuComplaints));await t.pumpAndSettle();expect(find.text('Destination /customer/support/complaints'),findsOneWidget);
    router.pop();await t.pumpAndSettle();await t.tap(find.text(AccountStrings.menuHelp));await t.pumpAndSettle();expect(find.text('Destination /customer/support'),findsOneWidget);
    router.pop();await t.pumpAndSettle();await t.tap(find.text(AccountStrings.changePassword));await t.pumpAndSettle();expect(find.widgetWithText(TextField,AccountStrings.currentPassword),findsOneWidget);
  });
  testWidgets('one vehicle opens directly and subscription card links to that car',(t)async{
    final router=await show(t,1);await t.tap(find.text(AccountStrings.menuAddons));await t.pumpAndSettle();expect(find.text('Destination /customer/vehicles/v1/addons'),findsOneWidget);
    router.pop();await t.pumpAndSettle();await t.tap(find.textContaining('Creta · HR00'));await t.pumpAndSettle();expect(find.text('Destination /customer/vehicles/v1/subscription'),findsOneWidget);
  });
  testWidgets('an empty account has no subscription cards or vehicle-selection route',(t)async{
    final router=await show(t,0);expect(find.text(AccountStrings.subscriptions),findsNothing);await t.tap(find.text(AccountStrings.menuAddons));await t.pumpAndSettle();expect(router.routeInformationProvider.value.uri.path,'/customer');
    await t.tap(find.text('Asha Rao'));await t.pumpAndSettle();expect(find.text(AccountStrings.editProfile),findsOneWidget);
  });
}
