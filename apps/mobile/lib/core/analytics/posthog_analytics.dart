import 'package:flutter/widgets.dart';
import 'package:posthog_flutter/posthog_flutter.dart';

import '../config/app_config.dart';
import 'analytics.dart';

/// PostHog behind [Analytics]. Replay records only when the build sets
/// `POSTHOG_REPLAY=true`. For now nothing is masked: recordings show every
/// screen as it is, touches included. What to mask is still to be decided.
/// The SDK itself always hides password fields.
class PostHogAnalytics implements Analytics {
  PostHogAnalytics(this._config);

  final AppConfig _config;

  @override
  bool get isActive => true;

  @override
  Future<void> init() async {
    final c = PostHogConfig(_config.posthogKey)
      // An unset CI variable arrives as an empty define.
      ..host = _config.posthogHost.isEmpty
          ? 'https://eu.i.posthog.com'
          : _config.posthogHost
      ..debug = _config.flavor == Flavor.test
      ..captureApplicationLifecycleEvents = true
      ..personProfiles = PostHogPersonProfiles.identifiedOnly
      // The SDK builds its recorder only when this is true at setup. It then
      // records from app start, so the sign-in screens are recorded too, for
      // every role.
      ..sessionReplay = _config.posthogReplay;
    c.sessionReplayConfig
      ..maskAllTexts = false
      ..maskAllImages = false
      ..maskAllPlatformViews = false
      ..captureTouches = true;
    c.errorTrackingConfig
      ..captureFlutterErrors = true
      ..capturePlatformDispatcherErrors = true
      ..captureNativeExceptions = true;
    await Posthog().setup(c);
  }

  @override
  void capture(String event, [Map<String, Object> properties = const {}]) {
    Posthog().capture(eventName: event, properties: properties);
  }

  @override
  void identify(String userId, {required String role}) {
    Posthog().identify(userId: userId, userProperties: {'role': role});
  }

  @override
  void reset() {
    Posthog().reset();
  }

  @override
  void screen(String name) {
    Posthog().screen(screenName: name);
  }

  @override
  void captureError(Object error, StackTrace? stack) {
    Posthog().captureException(error: error, stackTrace: stack);
  }

  @override
  Future<void> setEnabled(bool enabled) =>
      enabled ? Posthog().optIn() : Posthog().optOut();

  @override
  Widget wrap(Widget child) => PostHogWidget(child: child);

  @override
  Widget mask(Widget child) => PostHogMaskWidget(child: child);
}
