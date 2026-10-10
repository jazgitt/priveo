import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/theme.dart';
import 'crew/crew_profile_screen.dart';
import 'vehicles/vehicles_screen.dart';

/// The people screens, for the app's router to include. The router's redirect
/// rule has to let these paths through for the role they belong to.
final List<RouteBase> routes = [
  GoRoute(
    path: '/customer/vehicles',
    builder: (_, _) => const VehiclesScreen(),
    routes: [
      GoRoute(
        path: ':id',
        builder: (_, state) =>
            VehicleDetailScreen(vehicleId: state.pathParameters['id']!),
      ),
    ],
  ),
  GoRoute(
    path: '/crew/profile',
    builder: (_, _) =>
        Theme(data: crewTheme, child: const CrewProfileScreen()),
  ),
];
