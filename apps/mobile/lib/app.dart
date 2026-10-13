import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/config/app_config.dart';
import 'core/providers.dart';
import 'core/routing/router.dart';
import 'core/ui/theme.dart';
import 'l10n/app_localizations.dart';
import 'core/auth/auth_controller.dart';
import 'core/auth/session.dart';
import 'features/customer/home/customer_home_data.dart';
import 'features/support/feedback_tab.dart';
import 'features/support/feedback_sheet.dart';

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
    final router = ref.watch(routerProvider);
    final session = ref.watch(authControllerProvider).value;
    final confirmed = session?.role == Role.customer
        && (ref.watch(customerHomeProvider).value?.onboardingConfirmed ?? false);
    return MaterialApp.router(
      builder: (context, child) => ListenableBuilder(
        listenable: router.routeInformationProvider,
        builder: (context, _) {
          if (!confirmed || !router.routeInformationProvider.value.uri.path.startsWith('/customer')) {
            return child ?? const SizedBox.shrink();
          }
          return FeedbackSideTab(child: child ?? const SizedBox.shrink(), onOpen: () {
            final page = rootNavigatorKey.currentState?.overlay?.context;
            if (page != null) showFeedbackSheet(page);
          });
        },
      ),
      onGenerateTitle: (c) => AppLocalizations.of(c).appName,
      // The splash, login and customer screens. The crew and admin routes
      // set their own look in the router.
      theme: customerTheme,
      routerConfig: router,
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
