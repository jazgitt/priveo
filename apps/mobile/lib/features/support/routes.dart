import 'package:go_router/go_router.dart';

import 'checkin_screen.dart';
import 'complaints_screen.dart';
import 'crew_ratings_screen.dart';
import 'help_screen.dart';
import 'report_issue_screen.dart';

/// Paths of the support screens.
class SupportRoutes {
  static const help = '/customer/support';
  static const report = '/customer/support/report';
  static const complaints = '/customer/support/complaints';
  static String complaint(String id) => '/customer/support/complaints/$id';
  static const checkin = '/customer/support/checkin';
  static const crewRatings = '/crew/ratings';
}

/// Routes for the router to include. Open the report form for one clean with
/// `/customer/support/report?visit=<visit id>`.
final List<RouteBase> routes = [
  GoRoute(path: SupportRoutes.help, builder: (_, _) => const HelpScreen()),
  GoRoute(
    path: SupportRoutes.report,
    builder: (_, state) =>
        ReportIssueScreen(visitId: state.uri.queryParameters['visit']),
  ),
  GoRoute(
      path: SupportRoutes.complaints,
      builder: (_, _) => const ComplaintsScreen()),
  GoRoute(
    path: '/customer/support/complaints/:id',
    builder: (_, state) => ComplaintDetailScreen(id: state.pathParameters['id']!),
  ),
  GoRoute(
    path: SupportRoutes.checkin,
    builder: (_, state) =>
        CheckInScreen(subscriptionId: state.uri.queryParameters['subscription']),
  ),
  GoRoute(
      path: SupportRoutes.crewRatings,
      builder: (_, _) => const CrewRatingsScreen()),
];
