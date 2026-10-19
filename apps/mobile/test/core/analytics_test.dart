import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/analytics/analytics.dart';
import 'package:priveo/core/analytics/analytics_binding.dart';
import 'package:priveo/core/analytics/analytics_consent.dart';
import 'package:priveo/core/auth/auth_controller.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/providers.dart';

import '../support/fakes.dart';

class _Recorder extends NoopAnalytics {
  final calls = <String>[];

  @override
  bool get isActive => true;

  @override
  void identify(String userId, {required String role}) =>
      calls.add('identify $userId $role');

  @override
  void reset() => calls.add('reset');

  @override
  Future<void> setEnabled(bool enabled) async => calls.add('enabled $enabled');

  @override
  void screen(String name) => calls.add('screen $name');
}

void main() {
  test('screen names carry no record ids', () {
    expect(
      screenNameFor('/customer/visits/123e4567-e89b-12d3-a456-426614174000'),
      '/customer/visits/:id',
    );
    expect(screenNameFor('/admin/payments/42/pay'), '/admin/payments/:id/pay');
    expect(screenNameFor('/customer/settings'), '/customer/settings');
  });

  test('every role is identified, crew included', () async {
    for (final role in Role.values) {
      const id = '123e4567-e89b-12d3-a456-426614174000';
      final payload = base64Url
          .encode(utf8.encode(jsonEncode({'sub': id})))
          .replaceAll('=', '');
      final rec = _Recorder();
      final store = MemorySessionStore();
      await store.write(Session(
        role: role,
        displayName: 'Someone',
        accessToken: 'h.$payload.s',
        refreshToken: 'r',
      ));
      final container = ProviderContainer(overrides: [
        analyticsProvider.overrideWithValue(rec),
        sessionStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
      ]);
      addTearDown(container.dispose);
      await container.read(authControllerProvider.future);
      container.listen(analyticsBindingProvider, (_, _) {});
      expect(rec.calls, contains('identify $id ${role.name}'), reason: role.name);
    }
  });

  test('the no-op analytics is inactive and returns widgets unchanged', () {
    const a = NoopAnalytics();
    const child = SizedBox();
    expect(a.isActive, isFalse);
    expect(a.wrap(child), same(child));
    expect(a.mask(child), same(child));
  });

  test('the usage choice defaults to on, is saved, and reaches the SDK', () async {
    final rec = _Recorder();
    final consent = MemoryConsentStore();
    final container = ProviderContainer(overrides: [
      analyticsProvider.overrideWithValue(rec),
      consentStoreProvider.overrideWithValue(consent),
    ]);
    addTearDown(container.dispose);
    expect(await container.read(analyticsEnabledProvider.future), isTrue);

    await container.read(analyticsEnabledProvider.notifier).set(false);
    expect(await consent.read(), isFalse);
    expect(rec.calls, contains('enabled false'));

    await container.read(analyticsEnabledProvider.notifier).set(true);
    expect(await consent.read(), isTrue);
    expect(rec.calls, contains('enabled true'));
  });

  test('sign-in identifies by login id only, sign-out resets', () async {
    const id = '123e4567-e89b-12d3-a456-426614174000';
    final payload =
        base64Url.encode(utf8.encode(jsonEncode({'sub': id}))).replaceAll('=', '');
    final signedIn = Session(
      role: Role.customer,
      displayName: 'Aarav Mehta',
      accessToken: 'h.$payload.s',
      refreshToken: 'r',
    );
    final rec = _Recorder();
    final store = MemorySessionStore();
    await store.write(signedIn);
    final container = ProviderContainer(overrides: [
      analyticsProvider.overrideWithValue(rec),
      sessionStoreProvider.overrideWithValue(store),
      authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
    ]);
    addTearDown(container.dispose);
    await container.read(authControllerProvider.future);
    container.listen(analyticsBindingProvider, (_, _) {});

    expect(rec.calls, contains('identify $id customer'));
    expect(rec.calls.join(), isNot(contains('Aarav')));

    await container.read(authControllerProvider.notifier).logout();
    expect(rec.calls, contains('reset'));
  });
}
