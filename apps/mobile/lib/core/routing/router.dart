import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/admin_quick/home/admin_home_screen.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/crew/home/crew_home_screen.dart';
import '../../features/customer/home/customer_shell.dart';
import '../../features/splash/splash_screen.dart';
import '../auth/auth_controller.dart';
import '../auth/session.dart';

/// Redirect rule. The splash screen decides its own exit. After that:
/// no session means login, and a session means the shell for its role.
String? redirectFor(String location, Session? session) {
  if (location == '/splash') return null;
  if (session == null) return location == '/login' ? null : '/login';
  final home = session.role.homePath;
  return location == home ? null : home;
}

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.listen(authControllerProvider, (_, _) => refresh.value++);
  ref.onDispose(refresh.dispose);

  final router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      if (auth.isLoading) return null;
      return redirectFor(state.matchedLocation, auth.value);
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, _) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(path: '/customer', builder: (_, _) => const CustomerShell()),
      GoRoute(path: '/crew', builder: (_, _) => const CrewHomeScreen()),
      GoRoute(path: '/admin', builder: (_, _) => const AdminHomeScreen()),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});
