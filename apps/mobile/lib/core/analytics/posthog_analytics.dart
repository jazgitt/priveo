import 'package:flutter/widgets.dart';
import 'package:posthog_flutter/posthog_flutter.dart';

import '../config/app_config.dart';
import 'analytics.dart';

/// PostHog behind [Analytics]. Replay stays off until [startReplay] is called,
/// and text, images and platform views are masked. Touch positions are not
/// captured, because masking does not hide them.
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
      ..debug = _config.flavor == Flavor.dev
      ..captureApplicationLifecycleEvents = true
      ..personProfiles = PostHogPersonProfiles.identifiedOnly
      ..sessionReplay = false;
    c.sessionReplayConfig
      ..maskAllTexts = true
      ..maskAllImages = true
      ..captureTouches = false;
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
  Future<void> startReplay() async {
    if (_config.posthogReplay) await Posthog().startSessionRecording();
  }

  @override
  Future<void> stopReplay() => Posthog().stopSessionRecording();

  @override
  Widget wrap(Widget child) => PostHogWidget(child: child);

  @override
  Widget mask(Widget child) => PostHogMaskWidget(child: child);
}
