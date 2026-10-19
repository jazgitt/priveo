import 'package:flutter/widgets.dart';

/// What the app asks of product analytics. Only `posthog_analytics.dart`
/// knows the vendor, so a swap touches one file. No call may carry a name,
/// mobile number, email, address or vehicle number.
abstract class Analytics {
  /// False when no project key is set. Then nothing leaves the phone.
  bool get isActive;

  Future<void> init();

  void capture(String event, [Map<String, Object> properties = const {}]);

  /// [userId] is the login's UUID. [role] is `customer`, `crew` or `admin`.
  void identify(String userId, {required String role});

  /// Forget the user. Call on sign-out.
  void reset();

  void screen(String name);

  /// Records a handled error. [stack] may be null.
  void captureError(Object error, StackTrace? stack);

  Future<void> setEnabled(bool enabled);

  Future<void> startReplay();

  Future<void> stopReplay();

  /// Wraps the whole app so the vendor can see its frames. Returns [child]
  /// unchanged when inactive.
  Widget wrap(Widget child);

  /// Hides [child] from session replay. Returns [child] when inactive.
  Widget mask(Widget child);
}

class NoopAnalytics implements Analytics {
  const NoopAnalytics();

  @override
  bool get isActive => false;

  @override
  Future<void> init() async {}

  @override
  void capture(String event, [Map<String, Object> properties = const {}]) {}

  @override
  void identify(String userId, {required String role}) {}

  @override
  void reset() {}

  @override
  void screen(String name) {}

  @override
  void captureError(Object error, StackTrace? stack) {}

  @override
  Future<void> setEnabled(bool enabled) async {}

  @override
  Future<void> startReplay() async {}

  @override
  Future<void> stopReplay() async {}

  @override
  Widget wrap(Widget child) => child;

  @override
  Widget mask(Widget child) => child;
}
