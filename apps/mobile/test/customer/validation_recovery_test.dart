import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/customer/account/profile_screens.dart';
import 'package:priveo/features/customer/account/account_strings.dart';
import 'package:priveo/features/customer/calendar/defaults_sheet.dart';
import 'package:priveo/l10n/app_localizations.dart';
import '../contract/contract_http.dart';

Future<void> open(WidgetTester t,ContractHttp http,Widget screen)async{
  t.view.physicalSize=const Size(1000,2400);t.view.devicePixelRatio=2;addTearDown(t.view.reset);
  await t.pumpWidget(ProviderScope(retry:(_,_)=>null,overrides:[dioProvider.overrideWithValue(http.dio()),readRefreshProvider.overrideWith((_)=>const Stream<int>.empty())],child:MaterialApp(theme:customerTheme,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:Builder(builder:(c)=>Scaffold(body:TextButton(onPressed:()=>Navigator.of(c).push(MaterialPageRoute<void>(builder:(_)=>screen)),child:const Text('Open')))))));
  await t.tap(find.text('Open'));await t.pumpAndSettle();
}
Future<void> text(WidgetTester t,String label,String value)=>t.enterText(find.widgetWithText(TextField,label),value);
void main(){
  testWidgets('profile validation blocks invalid fields and API failure keeps editable values',(t)async{
    final http=ContractHttp();await open(t,http,const EditProfileScreen());
    await text(t,AccountStrings.firstName,'1');await text(t,AccountStrings.lastName,'2');await text(t,AccountStrings.mobile,'123');
    await t.tap(find.text(AccountStrings.save));await t.pumpAndSettle();
    expect(find.text(AccountStrings.enterFirstName),findsOneWidget);expect(find.text(AccountStrings.enterLastName),findsOneWidget);expect(find.text(AccountStrings.enterMobile),findsOneWidget);
    await text(t,AccountStrings.firstName,'Asha');await text(t,AccountStrings.lastName,'Rao');await text(t,AccountStrings.mobile,'9000000001');
    http.status=409;await t.tap(find.text(AccountStrings.save));await t.pumpAndSettle();expect(find.text('Please review the change.'),findsOneWidget);
    expect(t.widget<TextField>(find.widgetWithText(TextField,AccountStrings.firstName)).controller!.text,'Asha');
  });
  testWidgets('email validation and provider failures allow retrying send and verification',(t)async{
    final http=ContractHttp();await open(t,http,const ChangeEmailScreen());
    await t.tap(find.text(AccountStrings.sendCode));await t.pumpAndSettle();expect(find.text(AccountStrings.enterEmail),findsOneWidget);
    await text(t,AccountStrings.newEmail,'new@example.test');http.status=409;await t.tap(find.text(AccountStrings.sendCode));await t.pumpAndSettle();expect(find.text('Please review the change.'),findsOneWidget);
    http.status=200;await t.tap(find.text(AccountStrings.sendCode));await t.pumpAndSettle();expect(find.text(AccountStrings.emailCodeSent),findsOneWidget);
    await text(t,AccountStrings.code,'123456');http.status=409;await t.tap(find.text(AccountStrings.verify));await t.pumpAndSettle();expect(find.text('Please review the change.'),findsOneWidget);
    http.status=200;await t.tap(find.text(AccountStrings.verify));await t.pumpAndSettle();expect(find.text('Open'),findsOneWidget);
  });
  testWidgets('password policy blocks weak values and retries a rejected change',(t)async{
    final http=ContractHttp();await open(t,http,const ChangePasswordScreen());
    await text(t,AccountStrings.newPassword,'short');await t.tap(find.text(AccountStrings.save));await t.pumpAndSettle();expect(find.text(AccountStrings.passwordRule),findsNWidgets(2));
    await text(t,AccountStrings.currentPassword,'old');await text(t,AccountStrings.newPassword,'NewPassword12');http.status=409;
    await t.tap(find.text(AccountStrings.save));await t.pumpAndSettle();expect(find.text('Please review the change.'),findsOneWidget);
    http.status=200;await t.tap(find.text(AccountStrings.save));await t.pumpAndSettle();expect(find.text('Open'),findsOneWidget);
  });
  for(final fail in [false,true]){
    testWidgets('default preferences save changed fields and preserve frozen days; fail=$fail',(t)async{
      final http=ContractHttp();http.overrides['/v1/customer/vehicles/v1/preferences']={'cutoff_time':'09:00','interior_day':'Monday','applies_from':'2026-10-21','frozen_days_unchanged':2};
      bool? result;
      await open(t,http,Builder(builder:(c)=>Scaffold(body:TextButton(onPressed:()async{result=await showDefaultsSheet(c,vehicleId:'v1',cutoff:'09:00',interiorDay:'Friday');},child:const Text('Defaults')))));
      await t.tap(find.text('Defaults'));await t.pumpAndSettle();expect(t.widget<FilledButton>(find.byType(FilledButton)).onPressed,isNull);
      await t.tap(find.text('Friday'));await t.pumpAndSettle();await t.tap(find.text('Monday').last);await t.pumpAndSettle();
      http.status=fail?409:200;await t.tap(find.text('Save'));await t.pumpAndSettle();
      if(fail){expect(find.text('Please review the change.'),findsOneWidget);http.status=200;await t.tap(find.text('Save'));await t.pumpAndSettle();}
      expect(result,isTrue);expect(http.requests.last.data,{'interior_day':'Monday'});
    });
  }
}
