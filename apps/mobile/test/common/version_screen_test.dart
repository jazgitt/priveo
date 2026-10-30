import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:priveo/core/config/app_config.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/common/version/version_screen.dart';
import 'package:priveo/features/common/version/version_strings.dart';
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

const _test = AppConfig(
  flavor: Flavor.test,
  apiBaseUrl: 'https://priveo-api-test.vercel.app',
);
const _prod = AppConfig(
  flavor: Flavor.prod,
  apiBaseUrl: 'https://priveo-api-prod.vercel.app',
  buildStamp: '261030-101500',
);

Future<void> _pump(WidgetTester tester, AppConfig config, Widget home) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        appConfigProvider.overrideWithValue(config),
        notificationPrefsRepositoryProvider.overrideWithValue(_NoPrefs()),
        packageInfoProvider.overrideWith(
          (ref) async => PackageInfo(
            appName: 'Priveo',
            packageName: 'in.priveo.app',
            version: '0.2.7',
            buildNumber: '207',
          ),
        ),
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
        home: home,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a test build shows Test, its version and the test API', (
    tester,
  ) async {
    await _pump(tester, _test, const VersionScreen());
    expect(find.text('Test'), findsOneWidget);
    expect(find.text('0.2.7'), findsOneWidget);
    expect(find.text('207'), findsOneWidget);
    expect(find.text('priveo-api-test'), findsOneWidget);
    expect(find.text('https://priveo-api-test.vercel.app'), findsNothing);
    expect(find.text('in.priveo.app'), findsOneWidget);
    expect(find.text(VersionStrings.builtAt), findsNothing);
  });

  testWidgets(
    'a production build shows Production, the prod API and its stamp',
    (tester) async {
      await _pump(tester, _prod, const VersionScreen());
      expect(find.text('Prod'), findsOneWidget);
      expect(find.text('priveo-api-prod'), findsOneWidget);
      expect(find.text('261030-101500'), findsOneWidget);
      expect(find.text('Test'), findsNothing);
    },
  );

  testWidgets('Settings has a Version entry that opens the Version page', (
    tester,
  ) async {
    await _pump(tester, _test, const SettingsScreen());
    await tester.tap(find.text(VersionStrings.settingsEntry));
    await tester.pumpAndSettle();
    expect(find.text(VersionStrings.environment), findsOneWidget);
    expect(find.text('priveo-api-test'), findsOneWidget);
  });

  testWidgets('three taps on the server show its full address', (tester) async {
    await _pump(tester, _test, const VersionScreen());
    for (var i = 0; i < 2; i++) {
      await tester.tap(find.text('priveo-api-test'));
      await tester.pump();
    }
    expect(find.text('https://priveo-api-test.vercel.app'), findsNothing);
    await tester.tap(find.text('priveo-api-test'));
    await tester.pump();
    expect(find.text('https://priveo-api-test.vercel.app'), findsOneWidget);
  });
}
