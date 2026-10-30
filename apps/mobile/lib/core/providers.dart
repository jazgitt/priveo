import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../features/auth/data/auth_repository.dart';
import 'analytics/analytics.dart';
import 'analytics/analytics_consent.dart' show ConsentStore, SecureConsentStore;
import 'api/api.g.dart' show PriveoApi;
import 'auth/auth_controller.dart';
import 'auth/session.dart';
import 'config/app_config.dart';
import 'network/api_client.dart';

/// Overridden in `main_dev.dart` and `main_prod.dart`.
final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.dev);

/// The app's own version and build number (from pubspec.yaml). Tests override it.
final packageInfoProvider = FutureProvider<PackageInfo>(
  (ref) => PackageInfo.fromPlatform(),
);

/// Overridden in `runPriveo`. Tests keep this no-op.
final analyticsProvider = Provider<Analytics>((ref) => const NoopAnalytics());

final consentStoreProvider =
    Provider<ConsentStore>((ref) => SecureConsentStore());

final sessionStoreProvider =
    Provider<SessionStore>((ref) => SecureSessionStore());

final dioProvider = Provider<Dio>((ref) {
  final config = ref.watch(appConfigProvider);
  return buildDio(
    baseUrl: config.apiBaseUrl,
    accessToken: () => ref.read(authControllerProvider).value?.accessToken,
    refreshTokens: () =>
        ref.read(authControllerProvider.notifier).refreshTokens(),
  );
});

/// The client generated from the contract. Tests override this one provider.
final apiProvider =
    Provider<PriveoApi>((ref) => PriveoApi(ref.watch(dioProvider)));

final authRepositoryProvider =
    Provider<AuthRepository>((ref) => ApiAuthRepository(ref.watch(apiProvider)));
