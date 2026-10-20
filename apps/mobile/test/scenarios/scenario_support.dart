// Shared by the scenario widget tests: real client, real fixture API.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/app.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/config/app_config.dart';
import 'package:priveo/core/network/read_refresh.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/features/crew/crew_providers.dart';
import 'package:priveo/features/crew/upload/upload_queue.dart';

const scenarioUrl = String.fromEnvironment('SCENARIO_API_URL');
const scenarioManifestFile = String.fromEnvironment('SCENARIO_MANIFEST_FILE');
const scenarioPassword = String.fromEnvironment('SCENARIO_PASSWORD');
const scenarioAdminPassword = String.fromEnvironment('SCENARIO_ADMIN_PASSWORD');

/// Real time passes while the real client waits for the real server.
Future<void> until(
  WidgetTester tester,
  bool Function() done, {
  Duration timeout = const Duration(seconds: 25),
}) async {
  final end = DateTime.now().add(timeout);
  await tester.runAsync(() async {
    while (!done() && DateTime.now().isBefore(end)) {
      await Future<void>.delayed(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));
    }
  });
}

Future<void> untilFound(WidgetTester tester, Finder finder) async {
  await until(tester, () => finder.evaluate().isNotEmpty);
  expect(
    finder,
    findsWidgets,
    reason: 'The screen shows: ${visibleTexts().join(' | ')}',
  );
}

Future<void> tapFinder(WidgetTester tester, Finder finder) async {
  await untilFound(tester, finder);
  // A list builds only what is near the screen; bring the target into view.
  await tester.ensureVisible(finder.first);
  await tester.pump(const Duration(milliseconds: 200));
  await tester.tap(finder.first);
  await tester.pump(const Duration(milliseconds: 300));
}

Future<Session> signInApi(
  WidgetTester tester,
  String id,
  String password,
) async {
  Session? session;
  Object? failure;
  await tester.runAsync(() async {
    final container = ProviderContainer(
      overrides: [
        appConfigProvider.overrideWithValue(
          const AppConfig(
            flavor: Flavor.dev,
            apiBaseUrl: scenarioUrl,
          ),
        ),
      ],
    );
    try {
      session = await container
          .read(authRepositoryProvider)
          .login(id, password);
    } catch (e) {
      // runAsync would swallow it; rethrow outside.
      failure = e;
    } finally {
      container.dispose();
    }
  });
  if (failure != null) throw failure!;
  return session!;
}

/// The real app, signed in, with the real client. Only the plugins a test
/// cannot have (push, connectivity, SQLite) are replaced.
/// Opens the app. With a [session] it starts signed in; without one it starts
/// on the welcome screen, as a phone with no saved session does.
Future<void> openApp(WidgetTester tester, [Session? session]) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.5;
  addTearDown(tester.view.reset);
  final store = MemorySessionStore();
  if (session != null) await store.write(session);
  final container = ProviderContainer(
    overrides: [
      readRefreshProvider.overrideWith((ref) => const Stream<int>.empty()),
      appConfigProvider.overrideWithValue(
        const AppConfig(
          flavor: Flavor.dev,
          apiBaseUrl: scenarioUrl,
        ),
      ),
      sessionStoreProvider.overrideWithValue(store),
      uploadQueueStoreProvider.overrideWithValue(MemoryUploadQueueStore()),
      onlineEventsProvider.overrideWithValue(null),
    ],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const PriveoApp()),
  );
}

/// The manifest's scenarios by ID.
Map<String, Map<String, dynamic>> loadScenarios() {
  final manifest =
      jsonDecode(File(scenarioManifestFile).readAsStringSync())
          as Map<String, dynamic>;
  return {
    for (final s in manifest['scenarios'] as List)
      (s as Map<String, dynamic>)['id'] as String: s,
  };
}

/// Every non-empty text on screen, for failure messages.
List<String> visibleTexts() => find
    .byType(Text)
    .evaluate()
    .map((e) {
      final t = e.widget as Text;
      return t.data ?? t.textSpan?.toPlainText() ?? '';
    })
    .map((t) => t.replaceAll('\n', ' '))
    .where((t) => t.trim().isNotEmpty)
    .toList();

/// Lets timers started by the screen (messages, redirects) run out, so the
/// test ends with nothing pending.
Future<void> letTimersFinish(WidgetTester tester) async {
  // Let requests the last action started finish, then run out the clock: the
  // client's 20-second timeouts and the screens' message timers.
  // First let the screen start what the last tap asked for: a request that is
  // only started after the app is closed would never finish, and the fixture
  // API (one request at a time) would wait for it and stall the next test.
  await tester.pump(const Duration(milliseconds: 100));
  await tester.runAsync(() => Future<void>.delayed(const Duration(seconds: 3)));
  await tester.pump(const Duration(milliseconds: 100));
  // Close the app so screens cancel their own timers (the payment screen
  // polls every 10 seconds).
  await tester.pumpWidget(const SizedBox.shrink());
  for (var i = 0; i < 3; i++) {
    await tester.pump(const Duration(seconds: 10));
  }
}

/// Types into the last text field on screen, scrolling to it first when a
/// list has not built it yet.
Future<void> typeIntoLastField(WidgetTester tester, String text) async {
  final fields = find.byType(TextField);
  if (fields.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      fields,
      300,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await tester.ensureVisible(fields.last);
  await tester.enterText(fields.last, text);
  await tester.pump(const Duration(milliseconds: 300));
}

/// Scrolls the first scrollable until [finder] is built and on screen.
Future<void> scrollTo(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      finder,
      300,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await tester.ensureVisible(finder.first);
  await tester.pump(const Duration(milliseconds: 200));
}

/// Taps something in a long, lazily built list: waits for the screen, scrolls
/// until it is built, then taps it.
Future<void> tapScrolling(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() => Future<void>.delayed(const Duration(seconds: 2)));
  await tester.pump(const Duration(milliseconds: 200));
  await scrollTo(tester, finder);
  await tester.tap(finder.first);
  await tester.pump(const Duration(milliseconds: 300));
}
