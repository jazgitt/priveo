import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/auth/data/auth_repository.dart';
import 'api/api.g.dart' show PriveoApi;
import 'auth/auth_controller.dart';
import 'auth/session.dart';
import 'config/app_config.dart';
import 'network/api_client.dart';

/// Overridden in `main_dev.dart` and `main_prod.dart`.
final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.dev);

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
