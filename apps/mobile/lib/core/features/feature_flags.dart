import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../auth/auth_controller.dart';
import '../auth/session.dart';
import '../network/read_refresh.dart';
import '../providers.dart';

/// The admin's feature flags for the signed-in role. A flag that is missing,
/// or any flag before the first answer, is on, so a failed read never takes a
/// feature away.
class FeatureFlags {
  const FeatureFlags({this.flags = const {}, this.etag});

  final Map<String, bool> flags;
  final String? etag;

  /// Before the first server answer a missing key reads as on (fail open). A
  /// flag that defaults to off arrives from the server as false, so it is off
  /// once flags load; until then the server's `require_feature` is the real guard.
  bool isOn(String key) => flags[key] ?? true;
}

/// The last flags the server sent, kept on the phone so the next start needs
/// no wait.
abstract class FeatureFlagStore {
  Future<FeatureFlags?> read(Role role);
  Future<void> write(Role role, FeatureFlags flags);
}

class SecureFeatureFlagStore implements FeatureFlagStore {
  SecureFeatureFlagStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'feature_flags';
  final FlutterSecureStorage _storage;

  @override
  Future<FeatureFlags?> read(Role role) async {
    try {
      final text = await _storage.read(key: _key);
      if (text == null) return null;
      final j = jsonDecode(text) as Map<String, dynamic>;
      if (j['role'] != role.name) return null; // saved for another sign-in
      return FeatureFlags(
        flags: (j['flags'] as Map<String, dynamic>).cast<String, bool>(),
        etag: j['etag'] as String?,
      );
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> write(Role role, FeatureFlags flags) async {
    try {
      await _storage.write(
        key: _key,
        value: jsonEncode(
            {'role': role.name, 'etag': flags.etag, 'flags': flags.flags}),
      );
    } catch (_) {
      // The cache is a convenience only.
    }
  }
}

final featureFlagStoreProvider =
    Provider<FeatureFlagStore>((ref) => SecureFeatureFlagStore());

/// Reads the flags from the server. Returns null when nothing changed (304)
/// or when it could not be reached.
typedef FeatureFlagFetch = Future<FeatureFlags?> Function(
    Role role, String? etag);

final featureFlagFetchProvider = Provider<FeatureFlagFetch>((ref) {
  final dio = ref.watch(dioProvider);
  return (role, etag) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/v1/${role.name}/features',
      options: Options(
        headers: {'If-None-Match': ?etag},
        validateStatus: (s) => s == 200 || s == 304,
      ),
    );
    if (response.statusCode != 200 || response.data == null) return null;
    final body = response.data!;
    return FeatureFlags(
      flags: (body['flags'] as Map<String, dynamic>).cast<String, bool>(),
      etag: response.headers.value('etag'),
    );
  };
});

/// Loads the flags from the phone at once, then asks the server once: when a
/// customer or crew member signs in or the app opens signed in, and again only
/// on a hard refresh (pull to refresh, or returning after [awayBeforeRefresh]).
/// There is no timer. An unchanged answer is a 304 with no body.
class FeatureFlagsController extends Notifier<FeatureFlags> {
  Role? _role;
  int _generation = 0;

  @override
  FeatureFlags build() {
    final role = ref.watch(authControllerProvider.select((a) => a.value?.role));
    ref.listen(readRefreshProvider, (_, next) {
      if (next.hasValue) unawaited(_fetch());
    });
    _role = role;
    final generation = ++_generation;
    if (role == null || role == Role.admin) return const FeatureFlags();
    unawaited(_start(role, generation));
    return const FeatureFlags();
  }

  Future<void> _start(Role role, int generation) async {
    final cached = await ref.read(featureFlagStoreProvider).read(role);
    if (generation != _generation) return;
    if (cached != null) state = cached;
    await _fetch();
  }

  Future<void> _fetch() async {
    final role = _role;
    if (role == null || role == Role.admin) return;
    final generation = _generation;
    try {
      final fresh = await ref.read(featureFlagFetchProvider)(role, state.etag);
      if (fresh == null || generation != _generation) return;
      state = fresh;
      await ref.read(featureFlagStoreProvider).write(role, fresh);
    } catch (_) {
      // Keep what is shown: flags fail open.
    }
  }
}

final featureFlagsProvider =
    NotifierProvider<FeatureFlagsController, FeatureFlags>(
        FeatureFlagsController.new);

/// Whether one feature is on. Rebuilds the widget only when this flag changes.
final featureOnProvider = Provider.family<bool, String>((ref, key) =>
    ref.watch(featureFlagsProvider.select((f) => f.isOn(key))));

/// Shows [child] while the feature is on, else nothing.
class FeatureGate extends ConsumerWidget {
  const FeatureGate({
    super.key,
    required this.feature,
    required this.child,
    this.off = const SizedBox.shrink(),
  });

  final String feature;
  final Widget child;
  final Widget off;

  @override
  Widget build(BuildContext context, WidgetRef ref) =>
      ref.watch(featureOnProvider(feature)) ? child : off;
}
