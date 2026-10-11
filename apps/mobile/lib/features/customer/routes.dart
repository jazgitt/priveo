import 'package:go_router/go_router.dart';

import 'account/account_screen.dart';
import 'calendar/calendar_screen.dart';
import 'history/history_screen.dart';
import 'notifications/notifications_screen.dart';
import 'vehicles/vehicles_screen.dart';
import 'visit/visit_details_screen.dart';

export 'account/account_screen.dart' show AccountScreen;
export 'calendar/calendar_screen.dart' show CalendarScreen;

/// The customer slice's pages, for nesting under `/customer` at integration.
/// The tabs use [CalendarScreen] and [AccountScreen] directly. The screens
/// also push each other with the Navigator, so they work without these.
final List<GoRoute> routes = [
  GoRoute(
    path: 'visit/:id',
    builder: (_, state) =>
        VisitDetailsScreen(visitId: state.pathParameters['id']!),
  ),
  GoRoute(path: 'history', builder: (_, _) => const HistoryScreen()),
  GoRoute(path: 'vehicles', builder: (_, _) => const VehiclesScreen()),
  GoRoute(
    path: 'vehicles/:id',
    builder: (_, state) =>
        VehicleDetailScreen(vehicleId: state.pathParameters['id']!),
  ),
  GoRoute(
    path: 'notifications',
    builder: (_, _) => const NotificationsScreen(),
  ),
];
