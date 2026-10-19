enum Flavor { dev, prod }

class AppConfig {
  const AppConfig({
    required this.flavor,
    required this.apiBaseUrl,
    this.posthogKey = _posthogKey,
    this.posthogHost = _posthogHost,
    this.posthogReplay = _posthogReplay,
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

  /// The dev API address is set at build time:
  /// `--dart-define=API_BASE_URL=https://api-dev.example.com`.
  static const _devUrl = String.fromEnvironment(
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

  static const dev = AppConfig(
    flavor: Flavor.dev,
    apiBaseUrl: _devUrl,
  );

  static const prod = AppConfig(
    flavor: Flavor.prod,
    apiBaseUrl: _prodUrl,
  );
}
