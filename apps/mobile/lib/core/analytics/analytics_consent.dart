import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../auth/auth_controller.dart';
import '../auth/session.dart';
import '../providers.dart';
import 'analytics_binding.dart' show replayAllowedFor;

/// Keeps the customer's "Share usage data" choice on the phone (SET-05).
/// On by default.
abstract class ConsentStore {
  Future<bool> read();
  Future<void> write(bool enabled);
}

class SecureConsentStore implements ConsentStore {
  SecureConsentStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'analytics_enabled';
  final FlutterSecureStorage _storage;

  @override
  Future<bool> read() async {
    try {
      return await _storage.read(key: _key) != 'false';
    } catch (_) {
      return true;
    }
  }

  @override
  Future<void> write(bool enabled) => _storage.write(key: _key, value: '$enabled');
}

class MemoryConsentStore implements ConsentStore {
  MemoryConsentStore([this._enabled = true]);

  bool _enabled;

  @override
  Future<bool> read() async => _enabled;

  @override
  Future<void> write(bool enabled) async => _enabled = enabled;
}

/// Whether usage data is shared. Changing it takes effect at once.
class AnalyticsEnabled extends AsyncNotifier<bool> {
  @override
  Future<bool> build() => ref.read(consentStoreProvider).read();

  Future<void> set(bool enabled) async {
    await ref.read(consentStoreProvider).write(enabled);
    state = AsyncData(enabled);
    final analytics = ref.read(analyticsProvider);
    await analytics.setEnabled(enabled);
    if (!enabled) {
      await analytics.stopReplay();
      return;
    }
    final Session? session = ref.read(authControllerProvider).value;
    if (session != null && replayAllowedFor(session.role)) {
      await analytics.startReplay();
    }
  }
}

final analyticsEnabledProvider =
    AsyncNotifierProvider<AnalyticsEnabled, bool>(AnalyticsEnabled.new);
