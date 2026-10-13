import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ui/theme.dart';
import 'payments_screens.dart';

const adminPaymentsPath = '/admin/payments';
const adminAlertsPath = '/admin/payment-alerts';

/// The admin quick-action screens for money, in the admin cream look. They sit
/// under `/admin/`, so the role redirect must let those paths through.
final List<GoRoute> routes = [
  GoRoute(
    path: adminPaymentsPath,
    builder: (_, _) =>
        Theme(data: adminTheme, child: const PaymentsToConfirmScreen()),
  ),
  GoRoute(
    path: adminAlertsPath,
    builder: (_, _) =>
        Theme(data: adminTheme, child: const AdminAlertsScreen()),
  ),
];
