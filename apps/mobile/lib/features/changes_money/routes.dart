import 'package:go_router/go_router.dart';

import 'addon_screen.dart';
import 'billing_history_screen.dart';
import 'pay_screen.dart';
import 'skip_pause_screen.dart';
import 'subscription_screen.dart';

String skipPausePath(String vehicleId) => '/customer/vehicles/$vehicleId/skip-pause';
String subscriptionPath(String vehicleId) => '/customer/vehicles/$vehicleId/subscription';
String billingPath(String vehicleId) => '/customer/vehicles/$vehicleId/billing';
String addonsPath(String vehicleId) => '/customer/vehicles/$vehicleId/addons';
String payPath(String paymentId) => '/customer/pay/$paymentId';

/// Deep Spa without a subscription (ADD-15, open). The vehicle is optional.
String standalonePath([String? vehicleId]) =>
    vehicleId == null ? '/customer/deep-spa' : '/customer/deep-spa?vehicle=$vehicleId';

/// The customer's changes and money routes. The router adds these under the
/// customer role. They sit beside `/customer`, so the role redirect must let
/// paths under `/customer/` through.
final List<GoRoute> routes = [
  GoRoute(
    path: '/customer/vehicles/:vehicleId/skip-pause',
    builder: (_, s) => SkipPauseScreen(vehicleId: s.pathParameters['vehicleId']!),
  ),
  GoRoute(
    path: '/customer/vehicles/:vehicleId/subscription',
    builder: (_, s) => SubscriptionScreen(vehicleId: s.pathParameters['vehicleId']!),
  ),
  GoRoute(
    path: '/customer/vehicles/:vehicleId/billing',
    builder: (_, s) => BillingHistoryScreen(vehicleId: s.pathParameters['vehicleId']!),
  ),
  GoRoute(
    path: '/customer/vehicles/:vehicleId/addons',
    builder: (_, s) => AddonScreen(vehicleId: s.pathParameters['vehicleId']!),
  ),
  GoRoute(
    path: '/customer/pay/:paymentId',
    builder: (_, s) => PayScreen(paymentId: s.pathParameters['paymentId']!),
  ),
  GoRoute(
    path: '/customer/deep-spa',
    builder: (_, s) =>
        StandaloneDeepSpaScreen(vehicleId: s.uri.queryParameters['vehicle']),
  ),
];
