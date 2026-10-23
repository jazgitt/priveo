import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/auth/auth_controller.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/features/feature_flags.dart';
import 'package:priveo/core/features/feature_keys.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/routing/router.dart';

const customer = Session(
  role: Role.customer,
  displayName: 'C',
  accessToken: 'a',
  refreshToken: 'r',
);
const admin = Session(
  role: Role.admin,
  displayName: 'A',
  accessToken: 'a',
  refreshToken: 'r',
);

class _MemoryFlagStore implements FeatureFlagStore {
  FeatureFlags? saved;
  @override
  Future<FeatureFlags?> read(Role role) async => saved;
  @override
  Future<void> write(Role role, FeatureFlags flags) async => saved = flags;
}

Future<void> settle() => Future<void>.delayed(const Duration(milliseconds: 20));

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late _MemoryFlagStore store;
  late List<String?> asked;
  late FeatureFlags? answer;
  late ProviderContainer container;

  Future<ProviderContainer> start(Session? session) async {
    final sessions = MemorySessionStore();
    if (session != null) await sessions.write(session);
    container = ProviderContainer(
      overrides: [
        sessionStoreProvider.overrideWithValue(sessions),
        featureFlagStoreProvider.overrideWithValue(store),
        featureFlagFetchProvider.overrideWithValue((role, etag) async {
          asked.add(etag);
          return answer;
        }),
      ],
    );
    addTearDown(container.dispose);
    await container.read(authControllerProvider.future);
    container.listen(featureFlagsProvider, (_, _) {});
    await settle();
    return container;
  }

  setUp(() {
    store = _MemoryFlagStore();
    asked = [];
    answer = const FeatureFlags(
      flags: {FeatureKeys.deepSpa: false},
      etag: '"v1"',
    );
  });

  test('everything is on before any answer, and for a missing key', () {
    const f = FeatureFlags();
    expect(f.isOn(FeatureKeys.deepSpa), isTrue);
    expect(f.isOn('nonsense'), isTrue);
  });

  test('fetches once on sign-in, applies and saves it', () async {
    await start(customer);
    expect(asked, [null]);
    expect(
      container.read(featureFlagsProvider).isOn(FeatureKeys.deepSpa),
      isFalse,
    );
    expect(
      container.read(featureFlagsProvider).isOn(FeatureKeys.addons),
      isTrue,
    );
    expect(store.saved?.etag, '"v1"');
  });

  test('uses the saved flags at once and sends their ETag', () async {
    store.saved = const FeatureFlags(
      flags: {FeatureKeys.history: false},
      etag: '"old"',
    );
    answer = null; // 304: nothing changed
    await start(customer);
    expect(asked, ['"old"']);
    expect(
      container.read(featureFlagsProvider).isOn(FeatureKeys.history),
      isFalse,
    );
  });

  test('asks again only on a hard refresh, never on a timer', () async {
    await start(customer);
    await Future<void>.delayed(const Duration(seconds: 1));
    expect(asked, hasLength(1));
    container.read(readPulseProvider).refresh();
    await settle();
    expect(asked, [null, '"v1"']);
  });

  test('a failed read keeps what is shown', () async {
    await start(customer);
    answer = null;
    container.read(readPulseProvider).refresh();
    await settle();
    expect(
      container.read(featureFlagsProvider).isOn(FeatureKeys.deepSpa),
      isFalse,
    );
  });

  test('admins and signed-out people never ask', () async {
    await start(admin);
    expect(asked, isEmpty);
    await start(null);
    expect(asked, isEmpty);
  });

  group('routes', () {
    test('a flagged page maps to its flag', () {
      expect(FeatureKeys.forPath('/customer/deep-spa'), FeatureKeys.deepSpa);
      expect(
        FeatureKeys.forPath('/customer/vehicles/9/skip-pause'),
        FeatureKeys.skipPause,
      );
      expect(
        FeatureKeys.forPath('/customer/vehicles/9/addons'),
        FeatureKeys.addons,
      );
      expect(
        FeatureKeys.forPath('/customer/support/complaints/4'),
        FeatureKeys.complaints,
      );
      expect(FeatureKeys.forPath('/customer'), isNull);
      expect(FeatureKeys.forPath('/customer/vehicles/9'), isNull);
    });

    test('a page that is switched off sends the person home', () {
      bool off(String p) => FeatureKeys.forPath(p) == FeatureKeys.deepSpa;
      expect(
        redirectFor('/customer/deep-spa', customer, isOff: off),
        '/customer',
      );
      expect(redirectFor('/customer/history', customer, isOff: off), isNull);
      expect(redirectFor('/customer/deep-spa', customer), isNull);
    });
  });
}
