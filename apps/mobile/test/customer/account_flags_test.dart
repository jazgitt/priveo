import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/features/feature_flags.dart';
import 'package:priveo/core/features/feature_keys.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/changes_money/data/money_repository.dart';
import 'package:priveo/features/customer/account/account_data.dart';
import 'package:priveo/features/customer/account/account_sections.dart';
import 'package:priveo/features/customer/account/account_strings.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/l10n/app_localizations.dart';

import '../changes_money/fakes.dart';
import 'account_test.dart' show FakeAccount;

Future<void> show(WidgetTester t, Set<String> off) async {
  t.view.physicalSize = const Size(1000, 2800);
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(
    ProviderScope(
      retry: (_, _) => null,
      overrides: [
        readRefreshProvider.overrideWith((_) => const Stream<int>.empty()),
        accountRepositoryProvider.overrideWithValue(FakeAccount()),
        moneyRepositoryProvider.overrideWithValue(FakeMoneyRepository()),
        accountVehiclesProvider.overrideWith(
          (_) async => const [
            VehicleSummaryDto(
              id: 'v1',
              registration: 'HR00',
              model: 'Creta',
              society: 'Lake',
              subscriptionStatus: 'Active',
            ),
          ],
        ),
        featureOnProvider.overrideWith((ref, key) => !off.contains(key)),
      ],
      child: MaterialApp(
        theme: customerTheme,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: const Scaffold(
          body: SingleChildScrollView(child: AccountMoreLinks()),
        ),
      ),
    ),
  );
  await t.pumpAndSettle();
}

void main() {
  testWidgets('every account menu row shows while its feature is on', (
    t,
  ) async {
    await show(t, {});
    for (final label in [
      AccountStrings.menuAddons,
      AccountStrings.menuSkipPause,
      AccountStrings.menuComplaints,
      AccountStrings.menuHelp,
    ]) {
      expect(find.text(label), findsOneWidget);
    }
  });

  testWidgets('a switched-off feature leaves the account menu', (t) async {
    await show(t, {FeatureKeys.skipPause});
    expect(find.text(AccountStrings.menuSkipPause), findsNothing);
    expect(find.text(AccountStrings.menuAddons), findsOneWidget);
    expect(find.text(AccountStrings.menuComplaints), findsOneWidget);
  });

  testWidgets('add-ons, complaints and help can each be switched off', (
    t,
  ) async {
    await show(t, {
      FeatureKeys.addons,
      FeatureKeys.complaints,
      FeatureKeys.help,
    });
    expect(find.text(AccountStrings.menuAddons), findsNothing);
    expect(find.text(AccountStrings.menuComplaints), findsNothing);
    expect(find.text(AccountStrings.menuHelp), findsNothing);
    expect(find.text(AccountStrings.menuSkipPause), findsOneWidget);
  });
}
