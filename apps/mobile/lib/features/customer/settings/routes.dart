import 'package:go_router/go_router.dart';

import '../data/customer_reads_repository.dart';
import 'settings_screen.dart';

/// Paths a notification can open (NOTIF-02, CHK-05). They match the routes of
/// the visit, the pay screen and the support screens.
class NotificationPaths {
  const NotificationPaths._();

  static const settings = '/customer/settings';
  static const checkin = '/customer/support/checkin';

  static String visit(String id) => '/customer/visit/$id';
  static String payment(String id) => '/customer/pay/$id';
  static String complaint(String id) => '/customer/support/complaints/$id';

  /// Where tapping [n] goes, or null when it opens nothing.
  static String? of(NotificationDto n) {
    final id = n.refId;
    switch (n.refType) {
      case 'visit':
        return id == null ? null : visit(id);
      case 'payment':
        return id == null ? null : payment(id);
      case 'complaint':
        return id == null ? null : complaint(id);
      case 'checkin':
        return id == null ? checkin : '$checkin?subscription=$id';
    }
    final visitId = n.visitId;
    return visitId == null ? null : visit(visitId);
  }
}

/// Routes of the settings page, for `router.dart` to spread into its list.
/// The Account tab also opens Settings with the navigator, so it works
/// without these.
final List<GoRoute> routes = [
  GoRoute(
    path: NotificationPaths.settings,
    builder: (_, _) => const SettingsScreen(),
  ),
];
