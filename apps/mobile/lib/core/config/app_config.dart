enum Flavor { test, prod }

class AppConfig {
  const AppConfig({
    required this.flavor,
    required this.apiBaseUrl,
    this.posthogKey = _posthogKey,
    this.posthogHost = _posthogHost,
    this.posthogReplay = _posthogReplay,
    this.buildStamp = _buildStamp,
  });

  final Flavor flavor;
  final String apiBaseUrl;

  /// PostHog project key. Empty turns analytics off. The key is public by
  /// design, but it is still set at build time:
  /// `--dart-define=POSTHOG_KEY=phc_...`.
  final String posthogKey;

  /// `https://eu.i.posthog.com` or `https://us.i.posthog.com`. The region is
  /// an owner decision that is still open.
  final String posthogHost;

  /// Session replay is off unless `--dart-define=POSTHOG_REPLAY=true`.
  final bool posthogReplay;

  /// Set by `tool\push_apk.ps1` to the time of the build, and printed in the
  /// test startup log. The script looks for it inside the APK to prove the APK
  /// holds the code just compiled, not an old copy.
  final String buildStamp;

  /// The name of this build's environment, shown on the Version page.
  String get environmentName =>
      flavor == Flavor.prod ? 'Prod' : 'Test';

  /// The test API address is set at build time:
  /// `--dart-define=API_BASE_URL=https://api-test.example.com`.
  static const _testUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
  static const _prodUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.priveo.in',
  );
  static const _posthogKey = String.fromEnvironment('POSTHOG_KEY');
  static const _posthogHost = String.fromEnvironment(
    'POSTHOG_HOST',
    defaultValue: 'https://eu.i.posthog.com',
  );
  static const _posthogReplay = bool.fromEnvironment('POSTHOG_REPLAY');
  static const _buildStamp = String.fromEnvironment('BUILD_STAMP');

  static const test = AppConfig(
    flavor: Flavor.test,
    apiBaseUrl: _testUrl,
  );

  static const prod = AppConfig(
    flavor: Flavor.prod,
    apiBaseUrl: _prodUrl,
  );
}
