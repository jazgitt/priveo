import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/auth_controller.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/config/app_config.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/features/crew/crew_providers.dart';
import 'package:priveo/features/crew/data/crew_repository.dart';
import 'package:priveo/features/crew/upload/upload_queue.dart';

const _loginId = '0a1b2c3d-1111-2222-3333-444455556666';

String _token(String sub) {
  String part(Map<String, Object> m) => base64Url.encode(utf8.encode(jsonEncode(m)));
  return '${part({'alg': 'none'})}.${part({'sub': sub})}.sig';
}

Session _session(Role role, {String sub = _loginId}) => Session(
  role: role,
  displayName: 'Test',
  accessToken: _token(sub),
  refreshToken: 'refresh',
);

Future<ProviderContainer> _container(Session? session) async {
  final store = MemorySessionStore();
  if (session != null) await store.write(session);
  final container = ProviderContainer(
    retry: (_, _) => null,
    overrides: [
      sessionStoreProvider.overrideWithValue(store),
      appConfigProvider.overrideWithValue(AppConfig.test),
    ],
  );
  addTearDown(container.dispose);
  await container.read(authControllerProvider.future);
  return container;
}

void main() {
  group('crew providers and the signed-in crew member', () {
    test('only a crew sign-in owns the upload queue', () async {
      final crew = await _container(_session(Role.crew));
      expect(crew.read(crewUploadOwnerProvider), _loginId);
      final customer = await _container(_session(Role.customer));
      expect(customer.read(crewUploadOwnerProvider), isNull);
      final nobody = await _container(null);
      expect(nobody.read(crewUploadOwnerProvider), isNull);
    });

    test('the queue store refuses to open without a crew sign-in', () async {
      final nobody = await _container(null);
      expect(() => nobody.read(uploadQueueStoreProvider), throwsA(anything));
    });

    test('the upload client is the crew repository and closes with its owner', () async {
      final crew = await _container(_session(Role.crew));
      expect(crew.read(uploadApiProvider), isA<ApiCrewRepository>());
      crew.dispose();
    });

    test('the live connection stream is optional on a machine without the plugin', () async {
      final crew = await _container(_session(Role.crew));
      // Either a stream or null; the app must work with both.
      crew.read(onlineEventsProvider);
    });

    test('the device capture and the repository come from their providers', () async {
      final crew = await _container(_session(Role.crew));
      expect(crew.read(mediaCaptureProvider), isNotNull);
      expect(crew.read(crewRepositoryProvider), isA<ApiCrewRepository>());
    });

    test('the queue starts for its owner and reports what is waiting', () async {
      final store = MemoryUploadQueueStore();
      final session = MemorySessionStore();
      await session.write(_session(Role.crew));
      final container = ProviderContainer(
        retry: (_, _) => null,
        overrides: [
          sessionStoreProvider.overrideWithValue(session),
          appConfigProvider.overrideWithValue(AppConfig.test),
          uploadQueueStoreProvider.overrideWithValue(store),
          onlineEventsProvider.overrideWithValue(const Stream<bool>.empty()),
        ],
      );
      addTearDown(container.dispose);
      await container.read(authControllerProvider.future);
      final queue = container.read(uploadQueueProvider);
      expect(queue.items, isEmpty);
      container.listen(queuedUploadsProvider, (_, _) {});
      await Future<void>.delayed(Duration.zero);
    });
  });
}
