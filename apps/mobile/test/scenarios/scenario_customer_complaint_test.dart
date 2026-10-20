// A customer replies on a raised complaint (CMP), on the real screens against
// the fixture API. It has its own file: the reply is the last thing that test
// does, and a request still open when it ends would stall the one-request-at-a-time
// fixture API for the test after it. Needs the fixture API; see scenario_screens_test.dart.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/customer/home/home_schedule.dart';

import 'scenario_support.dart';

void main() {
  if (scenarioUrl.isEmpty) {
    test('scenario customer complaint', () {}, skip: 'SCENARIO_API_URL not set');
    return;
  }
  setUpAll(() => HttpOverrides.global = null);
  final scenarios = loadScenarios();
  String customer(String id) => scenarios[id]!['customer_login'] as String;

  Future<void> home(WidgetTester tester, String id) async {
    await openApp(
      tester,
      await signInApi(tester, customer(id), scenarioPassword),
    );
    await untilFound(tester, find.byType(GreetingLine));
  }

  group('complaints', () {
    testWidgets('C12 opens a raised complaint and replies on it [CMP-01, CMP-02]', (
      tester,
    ) async {
      await home(tester, 'C12');
      await tapFinder(tester, find.text('Support'));
      await tapFinder(tester, find.text('My complaints'));
      await tapFinder(tester, find.text('#C-1200'));

      // The reply box is the sign that the detail page, not the list, is open.
      await untilFound(tester, find.text('Write a reply'));
      expect(find.text('Synthetic Raised complaint'), findsWidgets);
      expect(find.text('Raised'), findsWidgets);
      expect(find.text('Synthetic thread entry'), findsWidgets);

      await typeIntoLastField(tester, 'Still dusty today.');
      await tapFinder(tester, find.text('Send'));
      // The reply joins the thread; the form clears.
      await until(
        tester,
        () =>
            find.text('Still dusty today.').evaluate().length == 1 &&
            find.text('Synthetic thread entry').evaluate().isNotEmpty,
        timeout: const Duration(seconds: 8),
      );
      expect(find.text('Still dusty today.'), findsOneWidget);
      await letTimersFinish(tester);
    });
  });
}
