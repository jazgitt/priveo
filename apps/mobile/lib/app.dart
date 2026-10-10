import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/config/app_config.dart';
import 'core/providers.dart';
import 'core/routing/router.dart';
import 'core/ui/theme.dart';
import 'l10n/app_localizations.dart';

/// Starts the app for one flavor.
void runPriveo(AppConfig config) {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(ProviderScope(
    overrides: [appConfigProvider.overrideWithValue(config)],
    child: const PriveoApp(),
  ));
}

class PriveoApp extends ConsumerWidget {
  const PriveoApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      onGenerateTitle: (c) => AppLocalizations.of(c).appName,
      theme: buildTheme(Brightness.light),
      darkTheme: buildTheme(Brightness.dark),
      themeMode: ThemeMode.system,
      routerConfig: ref.watch(routerProvider),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
    );
  }
}
