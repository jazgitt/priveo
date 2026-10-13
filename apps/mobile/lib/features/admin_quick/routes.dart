import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/theme.dart';
import 'complaints/complaints_screens.dart';
import 'actions/actions_screens.dart';
import 'actions/checklists_screen.dart';
import 'routes_paths.dart';
import 'scheduling/scheduling_screens.dart';

export 'routes_paths.dart';

Widget _admin(Widget child) => Theme(data: adminTheme, child: child);

/// The quick-action screens for complaints, feedback and scheduling, in the
/// admin cream look. The router includes them with `...admin_quick.routes`.
final List<RouteBase> routes = [
  GoRoute(path: AdminQuickPaths.checklists, builder: (_, _) => _admin(const AdminChecklistsScreen())),
  GoRoute(
    path: AdminQuickPaths.operations,
    builder: (_, s) => _admin(
      AdminOperationsScreen(
        initialDate: DateTime.tryParse(s.uri.queryParameters['date'] ?? ''),
      ),
    ),
  ),
  GoRoute(
    path: AdminQuickPaths.customers,
    builder: (_, _) => _admin(const AdminCustomersScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.customerPattern,
    builder: (_, s) => _admin(AdminCustomerScreen(id: s.pathParameters['id']!)),
  ),
  GoRoute(
    path: AdminQuickPaths.crew,
    builder: (_, _) => _admin(const AdminCrewScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.addons,
    builder: (_, _) => _admin(const AdminAddonsScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.checkins,
    builder: (_, _) => _admin(const AdminCheckinsScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.complaints,
    builder: (_, _) => _admin(const AdminComplaintsScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.complaintPattern,
    builder: (_, s) =>
        _admin(AdminComplaintScreen(id: s.pathParameters['id']!)),
  ),
  GoRoute(
    path: AdminQuickPaths.feedback,
    builder: (_, _) => _admin(const AdminFeedbackScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.needsScheduling,
    builder: (_, _) => _admin(const AdminNeedsSchedulingScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.day,
    builder: (_, _) => _admin(const AdminDayScheduleScreen()),
  ),
  GoRoute(
    path: AdminQuickPaths.capacity,
    builder: (_, _) => _admin(const AdminCapacityScreen()),
  ),
];
