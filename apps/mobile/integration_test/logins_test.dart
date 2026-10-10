// Runs the real app on a phone or emulator against a running API and signs
// in as each role. From apps/mobile:
//   flutter test integration_test --dart-define=API_BASE_URL=<url> \
//     --dart-define=LIVE_CUSTOMER_PASSWORD=... --dart-define=LIVE_CREW_PASSWORD=... \
//     --dart-define=LIVE_ADMIN_PASSWORD=...
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:priveo/features/auth/presentation/login_screen.dart';
import 'package:priveo/main_dev.dart' as app;

/// Login ID, password, and a label that only that role's home shows.
const _logins = [
  (
    'customer@priveo.test',
    String.fromEnvironment('LIVE_CUSTOMER_PASSWORD'),
    'Next service',
  ),
  ('9000000002', String.fromEnvironment('LIVE_CREW_PASSWORD'), 'Total'),
  (
    'priveopapa',
    String.fromEnvironment('LIVE_ADMIN_PASSWORD'),
    'Payments to confirm',
  ),
];

/// Waits for something that depends on the network or the splash.
Future<void> _waitFor(WidgetTester tester, Finder finder) async {
  for (var i = 0; i < 150; i++) {
    await tester.pump(const Duration(milliseconds: 200));
    if (finder.evaluate().isNotEmpty) return;
  }
  fail('Timed out waiting for $finder');
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('each role signs in, sees its home and signs out',
      (tester) async {
    app.main();
    final signOut = find.byTooltip('Sign out');
    final login = find.byType(LoginScreen);

    // The phone may still hold a session from an earlier run.
    await _waitFor(tester, find.byWidgetPredicate(
        (w) => w is LoginScreen || (w is IconButton && w.tooltip == 'Sign out')));
    if (signOut.evaluate().isNotEmpty) {
      await tester.tap(signOut);
      await _waitFor(tester, login);
    }

    for (final (id, password, homeLabel) in _logins) {
      expect(password, isNotEmpty, reason: 'No password given for $id');
      await tester.enterText(find.byType(TextField), id);
      await tester.tap(find.text('Continue'));
      await _waitFor(tester, find.text('Change'));
      await tester.enterText(find.byType(TextField), password);
      await tester.tap(find.text('Sign in').last);
      await _waitFor(tester, find.text(homeLabel));
      expect(login, findsNothing);

      await tester.tap(signOut);
      await _waitFor(tester, login);
    }
  });
}
