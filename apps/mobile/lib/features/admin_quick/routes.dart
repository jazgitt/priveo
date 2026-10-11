import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/theme.dart';
import 'complaints/complaints_screens.dart';
import 'routes_paths.dart';
import 'scheduling/scheduling_screens.dart';

export 'routes_paths.dart';

Widget _admin(Widget child) => Theme(data: adminTheme, child: child);

/// The quick-action screens for complaints, feedback and scheduling, in the
/// admin cream look. The router includes them with `...admin_quick.routes`.
final List<RouteBase> routes = [
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
