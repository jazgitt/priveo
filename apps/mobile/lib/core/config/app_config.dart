enum Flavor { dev, prod }

class AppConfig {
  const AppConfig({
    required this.flavor,
    required this.apiBaseUrl,
    required this.showDemoAccounts,
  });

  final Flavor flavor;
  final String apiBaseUrl;
  final bool showDemoAccounts;

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

  static const dev = AppConfig(
    flavor: Flavor.dev,
    apiBaseUrl: _devUrl,
    showDemoAccounts: true,
  );

  static const prod = AppConfig(
    flavor: Flavor.prod,
    apiBaseUrl: _prodUrl,
    showDemoAccounts: false,
  );
}
