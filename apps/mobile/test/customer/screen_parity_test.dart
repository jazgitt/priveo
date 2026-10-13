import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/customer/account/vehicle_account_section.dart';
import 'package:priveo/features/customer/account/account_data.dart';
import 'package:priveo/features/customer/calendar/day_card.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/support/faq_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';
import '../support/fakes.dart' show PhotoAccount;

Future<void> show(WidgetTester tester, Widget child) async {
  await tester.pumpWidget(ProviderScope(overrides: [accountRepositoryProvider.overrideWithValue(PhotoAccount())], child: MaterialApp(theme: customerTheme,
    localizationsDelegates: const [AppLocalizations.delegate, GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate],
    supportedLocales: AppLocalizations.supportedLocales,
    home: Scaffold(body: SingleChildScrollView(child: child)))));
  await tester.pumpAndSettle();
}

const car = VehicleDetailDto(id: 'v1', registration: 'HR01ZZ1234', model: 'Creta', society: 'Meadows',
    subscriptionStatus: 'Active', make: 'Hyundai', variant: 'SX', category: 'SUV', parking: 'P1-99',
    monthlyPriceRupees: 999, cutoffTime: '09:00', interiorDay: 'Monday', parkingBasement: 'P1',
    parkingNumber: '99', rcStatus: 'Verified', parkingBasements: ['P1', 'P2']);

void main() {
  testWidgets('verified RC stays verified and parking options come from its society', (tester) async {
    await show(tester, const VehicleAccountSection(vehicle: car));
    expect(find.text('Verified'), findsOneWidget);
    expect(find.text('Not uploaded'), findsNothing);
    await tester.tap(find.text('Edit parking'));
    await tester.pumpAndSettle();
    expect(find.text('P1'), findsOneWidget);
    expect(find.text('P2'), findsOneWidget);
    expect(find.text('B1'), findsNothing);
  });

  testWidgets('completed calendar card includes finish time and checked count', (tester) async {
    await show(tester, DayCard(date: DateTime(2026, 11, 7), today: DateTime(2026, 11, 8),
      fallbackCutoff: null, visits: [CalendarVisit(vehicleId: 'v1', date: DateTime(2026, 11, 7),
        status: 'Completed', services: const ['Cleaning-External'],
        finishedAt: DateTime(2026, 11, 7, 7, 30), checklistDone: 5, checklistTotal: 5)]));
    expect(find.textContaining('7:30 AM'), findsOneWidget);
    expect(find.textContaining('5 of 5 checks done'), findsOneWidget);
  });

  test('bundled FAQ parser keeps question order and the admin reactivation rule', () {
    final faq = parseFaqMarkdown('# Help\n## Late payment?\nContact Priveo to reactivate.\n\n## Proof?\nOpen Service Details.');
    expect(faq.map((f) => f.question), ['Late payment?', 'Proof?']);
    expect(faq.first.answer, 'Contact Priveo to reactivate.');
  });
}
