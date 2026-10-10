import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import 'session.dart';

class AuthController extends AsyncNotifier<Session?> {
  Future<bool>? _refreshing;

  @override
  Future<Session?> build() => ref.read(sessionStoreProvider).read();

  Session? get session => state.value;

  /// Throws [ApiFailure] when sign-in fails.
  Future<void> login(String loginId, String password) async {
    final s = await ref.read(authRepositoryProvider).login(loginId, password);
    await ref.read(sessionStoreProvider).write(s);
    state = AsyncData(s);
  }

  Future<void> logout() async {
    final repo = ref.read(authRepositoryProvider);
    await repo.logout();
    await ref.read(sessionStoreProvider).clear();
    state = const AsyncData(null);
  }

  /// Signs this login out everywhere, this phone included.
  /// Throws [ApiFailure] when the server could not be reached, and then
  /// nobody is signed out.
  Future<void> logoutAll() async {
    await ref.read(authRepositoryProvider).logoutAll();
    await ref.read(sessionStoreProvider).clear();
    state = const AsyncData(null);
  }

  /// Gets new tokens. Runs once at a time. Signs out when it fails.
  Future<bool> refreshTokens() => _refreshing ??= _doRefresh().whenComplete(() {
        _refreshing = null;
      });

  Future<bool> _doRefresh() async {
    final current = session;
    if (current == null) return false;
    try {
      final s = await ref
          .read(authRepositoryProvider)
          .refresh(current.refreshToken);
      await ref.read(sessionStoreProvider).write(s);
      state = AsyncData(s);
      return true;
    } catch (_) {
      await ref.read(sessionStoreProvider).clear();
      state = const AsyncData(null);
      return false;
    }
  }
}

final authControllerProvider =
    AsyncNotifierProvider<AuthController, Session?>(AuthController.new);
