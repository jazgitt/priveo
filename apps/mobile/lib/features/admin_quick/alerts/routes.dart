import 'package:go_router/go_router.dart';

import 'alerts_screen.dart';

class AlertsRoutes {
  static const alerts = '/admin/alerts';
}

/// Routes for the router to include.
final List<RouteBase> routes = [
  GoRoute(path: AlertsRoutes.alerts, builder: (_, _) => const AlertsScreen()),
];
