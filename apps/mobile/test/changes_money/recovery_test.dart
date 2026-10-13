import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/ui/widgets.dart';
import 'package:priveo/features/changes_money/data/money_models.dart';
import 'package:priveo/features/changes_money/routes.dart';
import '../contract/contract_http.dart';
import 'fakes.dart';
import '../support/fakes.dart' show FakePriveoApi;

class RecoveryMoney extends FakeMoneyRepository {
  void guard(){if(failure!=null)throw failure!;}
  @override Future<SubscriptionDto> subscription(String v)async{guard();return super.subscription(v);}
  @override Future<List<PaymentDto>> payments(String v)async{guard();return super.payments(v);}
  @override Future<PaymentDetailDto> paymentDetail(String id)async{guard();return super.paymentDetail(id);}
  @override Future<InvoiceDto> invoice(String id)async{guard();return super.invoice(id);}
  @override Future<AddonsDto> addons()async{guard();return super.addons();}
  @override Future<PaymentDetailDto> payNext(String v)async{guard();return super.payNext(v);}
  @override Future<PaymentDetailDto> markPaid(String id)async{guard();return super.markPaid(id);}
  @override Future<AddonRequestDto> requestAddon(String v,DateTime date,String finish)async{guard();return super.requestAddon(v,date,finish);}
  @override Future<AddonRequestDto> cancelAddon(String id)async{guard();return super.cancelAddon(id);}
}
void main(){
  for(final path in [subscriptionPath('v1'),billingPath('v1'),payPath('p1'),addonsPath('v1'),skipPausePath('v1')]){
    testWidgets('$path shows a recoverable load error',(t)async{
      final r=RecoveryMoney()..failure=const ApiFailure(code:'offline',message:'Try when connected');
      await openAt(t,path,money:r);expect(find.byType(ErrorView),findsWidgets);r.failure=null;
      await t.tap(find.text('Try again').first);await t.pumpAndSettle();expect(find.byType(ErrorView),findsNothing);
    });
  }
  testWidgets('failed next-payment and paid claims keep the original screen usable',(t)async{
    final r=RecoveryMoney();await openAt(t,subscriptionPath('v1'),money:r);r.failure=const ApiFailure(code:'conflict',message:'Payment is closed');
    await t.tap(find.text('Pay for next month'));await t.pumpAndSettle();expect(find.text('Payment is closed'),findsOneWidget);
    r.failure=null;await openAt(t,payPath('p1'),money:r);r.failure=const ApiFailure(code:'conflict',message:'Payment is closed');
    await t.tap(find.text("I've paid"));await t.pumpAndSettle();expect(find.text('Payment is closed'),findsOneWidget);expect(find.text('Pay by UPI'),findsOneWidget);
  });
  testWidgets('Spa booking and cancellation failures retain the request',(t)async{
    final r=RecoveryMoney();r.addonList=AddonsDto(offers:r.addonList.offers,requests:[AddonRequestDto(id:'a1',service:'Deep Spa',standalone:false,date:DateTime.now().add(const Duration(days:2)),finishBy:'12:00',status:'Requested',priceRupees:1500,paymentId:'p1',paymentStatus:'Due',canChange:true)]);
    await openAt(t,addonsPath('v1'),money:r);await t.tap(find.textContaining('Preferred date:').first);await t.pumpAndSettle();await t.tap(find.text('OK'));await t.pumpAndSettle();
    r.failure=const ApiFailure(code:'conflict',message:'Booking is closed');await t.tap(find.text('Confirm & pay'));await t.pumpAndSettle();expect(find.text('Booking is closed'),findsOneWidget);
    await t.ensureVisible(find.text('Cancel request'));await t.tap(find.text('Cancel request'));await t.pumpAndSettle();expect(find.text('Requested'),findsOneWidget);
  });
  testWidgets('Spa change dialog allows cancel, new date and time, then shows a rejected change',(t)async{
    final r=RecoveryMoney();final http=ContractHttp();r.addonList=AddonsDto(offers:r.addonList.offers,requests:[AddonRequestDto(id:'a1',service:'Deep Spa',standalone:false,date:DateTime.now().add(const Duration(days:2)),finishBy:'12:00',status:'Scheduled',priceRupees:1500,paymentId:'p1',paymentStatus:'Due',canChange:true,crewName:'Raj',startTime:'10:00',changeRequested:true)]);
    await openAt(t,addonsPath('v1'),money:r,dio:http.dio());
    await t.ensureVisible(find.text('Change date or time'));await t.tap(find.text('Change date or time'));await t.pumpAndSettle();await t.tap(find.text('Back'));await t.pumpAndSettle();expect(http.requests,isEmpty);
    await t.tap(find.text('Change date or time'));await t.pumpAndSettle();
    await t.tap(find.descendant(of:find.byType(AlertDialog),matching:find.byType(TextButton)).first);await t.pumpAndSettle();await t.tap(find.text('OK'));await t.pumpAndSettle();
    http.status=409;await t.tap(find.text('Continue'));await t.pumpAndSettle();await t.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:50)));await t.pumpAndSettle();
    expect(http.requests.last.method,'PATCH');expect(http.requests.last.path,'/v1/customer/addons/a1');
    expect(find.text('Please review the change.'),findsOneWidget,reason:t.widgetList<Text>(find.byType(Text)).map((w)=>w.data).join(' | '));
  });
  testWidgets('closed Spa changes open the configured helpline and explain contact errors',(t)async{
    final r=RecoveryMoney();final http=ContractHttp();final links=<Uri>[];
    http.overrides['/v1/auth/support-contact']={'helpline':'+910000000001'};
    r.addonList=AddonsDto(offers:r.addonList.offers,requests:[AddonRequestDto(id:'a1',service:'Deep Spa',standalone:true,date:DateTime.now().add(const Duration(days:2)),finishBy:'12:00',status:'Scheduled',priceRupees:1500,paymentId:'p1',paymentStatus:'Due',canChange:false)]);
    await openAt(t,addonsPath('v1'),money:r,dio:http.dio(),linkOpener:(uri)async{links.add(uri);return true;});
    await t.ensureVisible(find.text('Changes are closed. Call support for help.'));await t.tap(find.text('Changes are closed. Call support for help.'));await t.pumpAndSettle();
    expect(links.single.scheme,'tel');expect(links.single.path,'+910000000001');
    http.status=409;await t.tap(find.text('Changes are closed. Call support for help.'));await t.pumpAndSettle();expect(find.text('Please review the change.'),findsOneWidget);
  });
  testWidgets('standalone selector offers only owned vehicles without a subscription',(t)async{
    await openAt(t,standalonePath(),money:RecoveryMoney(),api:FakePriveoApi());
    expect(find.text('Choose your vehicle'),findsOneWidget);expect(find.text('MH 12 AB 1234'),findsNothing);
    await t.tap(find.text('DL 3 CAB 1234'));await t.pumpAndSettle();expect(find.text('Confirm & pay'),findsOneWidget);
  });
}
