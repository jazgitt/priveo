import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/auth_controller.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/providers.dart';

import '../support/fakes.dart';

const a = Session(role: Role.crew, displayName: 'A', accessToken: 'a', refreshToken: 'refresh-a');
const b = Session(role: Role.crew, displayName: 'B', accessToken: 'b', refreshToken: 'refresh-b');

class _Repository extends FakeAuthRepository {
  final pending = Completer<Session>();
  @override
  Future<Session> refresh(String refreshToken) => pending.future;
  @override
  Future<Session> login(String loginId, String password) async => b;
}

void main() {
  for (final fail in [false, true]) {
    test('late refresh ${fail ? 'failure' : 'success'} cannot replace another account', () async {
      final repo = _Repository();
      final store = MemorySessionStore();
      await store.write(a);
      final container = ProviderContainer(overrides: [
        sessionStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(repo),
      ]);
      addTearDown(container.dispose);
      await container.read(authControllerProvider.future);
      final controller = container.read(authControllerProvider.notifier);
      final refreshing = controller.refreshTokens();
      await controller.login('b', 'password');
      if (fail) {
        repo.pending.completeError(StateError('Old refresh expired'));
      } else {
        repo.pending.complete(a);
      }
      expect(await refreshing, isFalse);
      expect(container.read(authControllerProvider).value?.refreshToken, b.refreshToken);
      expect((await store.read())?.refreshToken, b.refreshToken);
    });
  }

  test('late refresh cannot restore a signed-out account', () async {
    final repo = _Repository();
    final store = MemorySessionStore();
    await store.write(a);
    final container = ProviderContainer(overrides: [
      sessionStoreProvider.overrideWithValue(store),
      authRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);
    await container.read(authControllerProvider.future);
    final controller = container.read(authControllerProvider.notifier);
    final refreshing = controller.refreshTokens();
    await controller.logout();
    repo.pending.complete(a);
    expect(await refreshing, isFalse);
    expect(container.read(authControllerProvider).value, isNull);
    expect(await store.read(), isNull);
  });
}
