import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/admin_quick/home/admin_home_screen.dart';
import '../../features/admin_quick/alerts/routes.dart' as alerts;
import '../../features/admin_quick/payments/routes.dart' as payments;
import '../../features/admin_quick/routes.dart' as admin_quick;
import '../../features/auth/presentation/login_screen.dart';
import '../../features/changes_money/routes.dart' as money;
import '../../features/crew/home/crew_home_screen.dart';
import '../../features/customer/home/customer_shell.dart';
import '../../features/customer/routes.dart' as customer_pages;
import '../../features/people/routes.dart' as people;
import '../../features/support/routes.dart' as support;
import '../../features/splash/splash_screen.dart';
import '../auth/auth_controller.dart';
import '../auth/session.dart';
import '../features/feature_flags.dart';
import '../features/feature_keys.dart';
import '../ui/theme.dart';

/// Redirect rule. The splash screen decides its own exit. After that:
/// no session means login, and a session means the shell for its role.
///
/// [isOff] says whether the admin has switched off the feature behind a path.
/// A page that is off sends the person home, so a stale link or a screen left
/// open shows nothing the admin has taken away.
String? redirectFor(String location, Session? session,
    {bool Function(String path)? isOff}) {
  if (location == '/splash') return null;
  if (session == null) return location == '/login' ? null : '/login';
  final home = session.role.homePath;
  if (isOff != null && location != home && isOff(location)) return home;
  // The role's own pages sit under its home path. Support and alerts are
  // `/customer/support`, `/crew/ratings` and `/admin/alerts`.
  return location == home || location.startsWith('$home/') ? null : home;
}

final rootNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.listen(authControllerProvider, (_, _) => refresh.value++);
  // A flag changed on a refresh: check the open page again.
  ref.listen(featureFlagsProvider, (_, _) => refresh.value++);
  ref.onDispose(refresh.dispose);

  final router = GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      if (auth.isLoading) return null;
      final flags = ref.read(featureFlagsProvider);
      return redirectFor(state.matchedLocation, auth.value, isOff: (path) {
        final key = FeatureKeys.forPath(path);
        return key != null && !flags.isOn(key);
      });
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, _) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(
        path: '/customer',
        builder: (_, _) => const CustomerShell(),
        routes: customer_pages.routes,
      ),
      GoRoute(
        path: '/crew',
        builder: (_, _) =>
            Theme(data: crewTheme, child: const CrewHomeScreen()),
      ),
      GoRoute(
        path: '/admin',
        builder: (_, _) =>
            Theme(data: adminTheme, child: const AdminHomeScreen()),
      ),
      ...support.routes,
      ...alerts.routes,
      ...payments.routes,
      ...admin_quick.routes,
      ...money.routes,
      // The people slice's vehicle pages are replaced by the customer slice's.
      ...people.routes.where((r) => r is GoRoute && r.path == '/crew/profile'),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});
