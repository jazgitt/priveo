import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/analytics/analytics.dart';
import 'package:priveo/core/analytics/analytics_consent.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/customer/cust_strings.dart';
import 'package:priveo/features/customer/settings/notification_prefs_repository.dart';
import 'package:priveo/features/customer/settings/settings_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';

class _NoPrefs implements NotificationPrefsRepository {
  @override
  Future<List<NotificationPrefDto>> load() async => const [];

  @override
  Future<List<NotificationPrefDto>> set(String event, bool enabled) async =>
      const [];
}

class _Active extends NoopAnalytics {
  final calls = <String>[];

  @override
  bool get isActive => true;

  @override
  Future<void> setEnabled(bool enabled) async => calls.add('enabled $enabled');

  @override
  Future<void> stopReplay() async => calls.add('replay off');
}

Future<void> _pump(WidgetTester tester, List<Override> overrides) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(ProviderScope(
    overrides: [
      notificationPrefsRepositoryProvider.overrideWithValue(_NoPrefs()),
      ...overrides,
    ],
    child: MaterialApp(
      theme: customerTheme,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: const SettingsScreen(),
    ),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the usage switch is hidden when analytics is not set up',
      (tester) async {
    await _pump(tester, []);
    expect(find.text(CustStrings.settingsUsageTitle), findsNothing);
  });

  testWidgets('the usage switch is on by default and turns sharing off',
      (tester) async {
    final analytics = _Active();
    final store = MemoryConsentStore();
    await _pump(tester, [
      analyticsProvider.overrideWithValue(analytics),
      consentStoreProvider.overrideWithValue(store),
    ]);
    final tile = find.widgetWithText(
        SwitchListTile, CustStrings.settingsUsageTitle);
    expect(tester.widget<SwitchListTile>(tile).value, isTrue);

    await tester.tap(tile);
    await tester.pumpAndSettle();

    expect(tester.widget<SwitchListTile>(tile).value, isFalse);
    expect(await store.read(), isFalse);
    expect(analytics.calls, containsAllInOrder(['enabled false', 'replay off']));
  });

  testWidgets('a saved opt-out shows the switch off', (tester) async {
    await _pump(tester, [
      analyticsProvider.overrideWithValue(_Active()),
      consentStoreProvider.overrideWithValue(MemoryConsentStore(false)),
    ]);
    final tile = find.widgetWithText(
        SwitchListTile, CustStrings.settingsUsageTitle);
    expect(tester.widget<SwitchListTile>(tile).value, isFalse);
  });
}
