import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/auth_controller.dart';
import '../../../core/auth/session.dart';
import '../../../core/providers.dart';
import '../../customer/data/customer_reads_repository.dart';

/// Where the phone's push token comes from. Firebase is not in the app yet,
/// so the default gives none and nothing is registered. When FCM is added,
/// override [pushTokenProvider] with a provider that asks it (NOTIF-01).
abstract class PushTokenProvider {
  /// The FCM token, or null when push is not available (no Firebase, or the
  /// person refused the operating system's permission).
  Future<String?> token();

  /// `android` or `ios`.
  String get platform;
}

class NoPushTokenProvider implements PushTokenProvider {
  const NoPushTokenProvider();

  @override
  Future<String?> token() async => null;

  @override
  String get platform =>
      defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android';
}

final pushTokenProvider = Provider<PushTokenProvider>(
  (ref) => const NoPushTokenProvider(),
);

/// Registers this phone for push after sign-in: the customer through the
/// existing `registerDevice`, crew and admin through `/v1/<role>/devices`.
/// Watch it from a signed-in screen. It does nothing without a token, and a
/// failure never stops the app.
final pushRegistrationProvider = FutureProvider<void>((ref) async {
  final session = ref.watch(authControllerProvider).value;
  if (session == null) return;
  final provider = ref.watch(pushTokenProvider);
  try {
    final token = await provider.token();
    if (token == null || token.isEmpty) return;
    if (session.role == Role.customer) {
      await ref
          .read(customerReadsProvider)
          .registerDevice(token, provider.platform);
    } else {
      await ref
          .read(dioProvider)
          .put<void>(
            '/v1/${session.role.name}/devices',
            data: {'token': token, 'platform': provider.platform},
          );
    }
  } on DioException {
    // Push is a convenience. Try again next time the app starts.
  } catch (_) {
    // Same.
  }
});
