import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/features/customer/home/customer_home_data.dart';

import '../support/fakes.dart';

void main() {
  test('open Home observes externally changed onboarding state on a refresh pulse', () async {
    final ticks = StreamController<int>();
    final server = FakePriveoApi(onboardingConfirmed: false);
    final container = ProviderContainer(overrides: [
      apiProvider.overrideWithValue(server),
      readRefreshProvider.overrideWith((ref) => ticks.stream),
    ]);
    final sub = container.listen(customerHomeProvider, (_, _) {});
    expect((await container.read(customerHomeProvider.future)).onboardingConfirmed, isFalse);
    server.onboardingConfirmed = true; // A write made by another client.
    ticks.add(1);
    await Future<void>.delayed(Duration.zero);
    expect((await container.read(customerHomeProvider.future)).onboardingConfirmed, isTrue);
    sub.close();
    container.dispose();
    await ticks.close();
  });

  testWidgets('refresh on resume only after 5 minutes away, never on a timer', (tester) async {
    var clock = DateTime(2026, 10, 16, 9);
    final container = ProviderContainer(overrides: [
      readPulseProvider.overrideWith((ref) {
        final pulse = ReadPulse(now: () => clock);
        ref.onDispose(pulse.dispose);
        return pulse;
      }),
    ]);
    final pulses = <int>[];
    final sub = container.listen(readRefreshProvider, (_, value) {
      if (value.hasValue) pulses.add(value.value!);
    });
    await tester.pump();
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump(const Duration(seconds: 30));
    expect(pulses, isEmpty);
    // Back after 4 minutes: nothing refreshes.
    clock = clock.add(const Duration(minutes: 4));
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(pulses, isEmpty);
    // Away for 5 minutes: it refreshes once.
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    clock = clock.add(const Duration(minutes: 5));
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(pulses.length, 1);
    // There is no polling: time passing in the foreground emits nothing.
    await tester.pump(const Duration(seconds: 90));
    expect(pulses.length, 1);
    sub.close();
    container.dispose();
  });
}
