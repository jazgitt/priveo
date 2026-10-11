import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/theme.dart';
import 'home/crew_home_screen.dart';

/// The crew's routes, for `router.dart` to spread into its list. Screens
/// opened from the home (job card, perform service, could not complete,
/// manager, profile) are pushed on the navigator, because the redirect rule
/// keeps a crew session on `/crew`.
final List<RouteBase> routes = [
  GoRoute(
    path: '/crew',
    builder: (_, _) => Theme(data: crewTheme, child: const CrewHomeScreen()),
  ),
];
