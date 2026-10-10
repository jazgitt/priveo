import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/auth/presentation/login_screen.dart';
import 'package:priveo/features/crew/home/crew_home_screen.dart';

import 'support/fakes.dart';
import 'package:priveo/core/auth/session.dart';

Future<void> signIn(WidgetTester tester, String id, String password) async {
  await enterId(tester, id);
  await tester.enterText(find.byType(TextField), password);
  await tester.tap(find.text('Sign in').last);
  await tester.pumpAndSettle();
}

Future<void> enterId(WidgetTester tester, String id) async {
  await tester.enterText(find.byType(TextField), id);
  await tester.tap(find.text('Continue'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('splash goes to login when signed out', (tester) async {
    await pumpApp(tester);
    expect(find.byType(LoginScreen), findsNothing);
    await passSplash(tester);
    expect(find.byType(LoginScreen), findsOneWidget);
  });

  testWidgets('splash with reduce motion is short', (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await pumpApp(tester);
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);
  });

  testWidgets('wrong password shows the API message', (tester) async {
    await pumpApp(tester);
    await passSplash(tester);
    await signIn(tester, 'priveopapa', 'wrong');
    expect(find.text(FakeAuthRepository.wrongMessage), findsOneWidget);
    expect(find.byType(LoginScreen), findsOneWidget);
  });

  testWidgets('empty fields are checked before calling the API',
      (tester) async {
    await pumpApp(tester);
    await passSplash(tester);
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    expect(find.text('Enter your email, mobile number or user ID.'),
        findsOneWidget);

    await enterId(tester, 'priveopapa');
    await tester.tap(find.text('Sign in').last);
    await tester.pumpAndSettle();
    expect(find.text('Enter your password.'), findsOneWidget);
    // Only a customer can reset a password with an emailed code.
    expect(find.text('Forgot password?'), findsNothing);

    await tester.tap(find.text('Change'));
    await tester.pumpAndSettle();
    expect(find.text('Continue'), findsOneWidget);
  });

  testWidgets('an email that is not registered shows the API message',
      (tester) async {
    await pumpApp(tester);
    await passSplash(tester);
    await enterId(tester, 'stranger@priveo.test');
    expect(find.text(FakeAuthRepository.notRegistered), findsOneWidget);
    expect(find.text('Continue'), findsOneWidget);
  });

  testWidgets('first sign-in: code, then a password, then home',
      (tester) async {
    final auth = FakeAuthRepository();
    await pumpApp(tester, auth: auth);
    await passSplash(tester);
    await enterId(tester, FakeAuthRepository.newCustomer);
    expect(find.text('Enter the code'), findsOneWidget);
    expect(find.textContaining(FakeAuthRepository.newCustomer), findsOneWidget);
    expect(find.text('Resend code in 00:30'), findsOneWidget);

    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    expect(find.text('Enter the 6-digit code.'), findsOneWidget);

    // Only digits are taken, six at most, as when a code is pasted.
    await tester.enterText(find.byType(TextField), '12a34567');
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    expect(find.text(FakeAuthRepository.wrongCode), findsOneWidget);

    await tester.enterText(find.byType(TextField), FakeAuthRepository.code);
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    expect(find.text('Set a password'), findsOneWidget);

    Future<void> save(String password, String confirm) async {
      await tester.enterText(find.byType(TextField).at(0), password);
      await tester.enterText(find.byType(TextField).at(1), confirm);
      await tester.tap(find.text('Save and continue'));
      await tester.pumpAndSettle();
    }

    await save('short1', 'short1');
    expect(auth.passwordSet, isNull);
    await save('carwash2026', 'carwash2027');
    expect(find.text('The two passwords do not match.'), findsOneWidget);
    await save('carwash2026', 'carwash2026');
    expect(auth.passwordSet, 'carwash2026');
    expect(find.text('Hello,'), findsOneWidget);
  });

  testWidgets('the code can be sent again when the countdown ends',
      (tester) async {
    final auth = FakeAuthRepository();
    await pumpApp(tester, auth: auth);
    await passSplash(tester);
    await enterId(tester, FakeAuthRepository.newCustomer);
    expect(find.text('Resend code'), findsNothing);
    await tester.pump(const Duration(seconds: 2));
    expect(find.text('Resend code in 00:28'), findsOneWidget);
    await tester.pump(const Duration(seconds: 28));
    await tester.tap(find.text('Resend code'));
    await tester.pumpAndSettle();
    expect(auth.codesSent, 2);
    expect(find.text('Resend code in 00:30'), findsOneWidget);
  });

  testWidgets('forgot password sends a code', (tester) async {
    final auth = FakeAuthRepository();
    await pumpApp(tester, auth: auth);
    await passSplash(tester);
    await enterId(tester, 'customer@priveo.test');
    await tester.tap(find.text('Forgot password?'));
    await tester.pumpAndSettle();
    expect(auth.codesSent, 1);
    expect(find.text('Enter the code'), findsOneWidget);

    await tester.tap(find.text('Change email'));
    await tester.pumpAndSettle();
    expect(find.text('Continue'), findsOneWidget);
  });

  testWidgets('customer login lands on the customer home', (tester) async {
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 2;
    addTearDown(tester.view.reset);
    await pumpApp(tester);
    await passSplash(tester);
    await signIn(tester, 'customer@priveo.test', 'secret');
    expect(find.text('Hello,'), findsOneWidget);
    expect(find.text('Aarav'), findsOneWidget);
    expect(find.text('MH 12 AB 1234'), findsOneWidget);
    expect(find.text('07-Nov-26'), findsOneWidget);
    for (final a in [
      'Skip or Pause',
      'Service History',
      'Give Feedback',
      'Report an Issue',
    ]) {
      expect(find.text(a), findsOneWidget);
    }
    await tester.tap(find.text('Calendar'));
    await tester.pumpAndSettle();
    expect(find.text('Coming soon'), findsOneWidget);
  });

  testWidgets('crew login lands on the crew home', (tester) async {
    await pumpApp(tester);
    await passSplash(tester);
    await signIn(tester, '9000000002', 'secret');
    // The cards come from the crew API (see test/crew), which these tests
    // do not fake. The role's own home is what they check.
    expect(find.byType(CrewHomeScreen), findsOneWidget);
  });

  testWidgets('admin login lands on the admin home', (tester) async {
    await pumpApp(tester);
    await passSplash(tester);
    await signIn(tester, 'priveopapa', 'secret');
    expect(find.text('Payments to confirm'), findsOneWidget);
    expect(find.text('Flat A-101'), findsOneWidget);
    expect(find.text('₹1,499'), findsOneWidget);
  });

  testWidgets('a stored session skips login and sign out returns to it',
      (tester) async {
    final store = MemorySessionStore();
    await store.write(crewSession);
    final auth = FakeAuthRepository();
    await pumpApp(tester, store: store, auth: auth);
    await passSplash(tester);
    expect(find.byType(CrewHomeScreen), findsOneWidget);

    await tester.tap(find.byTooltip('Sign out'));
    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);
    expect(auth.logoutCalls, 1);
    expect(await store.read(), isNull);
  });

  testWidgets('admin signs out of all devices after confirming',
      (tester) async {
    final store = MemorySessionStore();
    await store.write(adminSession);
    final auth = FakeAuthRepository();
    await pumpApp(tester, store: store, auth: auth);
    await passSplash(tester);

    await tester.tap(find.text('Sign out of all devices'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(auth.logoutAllCalls, 0);

    await tester.tap(find.text('Sign out of all devices'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sign out'));
    await tester.pumpAndSettle();
    expect(auth.logoutAllCalls, 1);
    expect(find.byType(LoginScreen), findsOneWidget);
    expect(await store.read(), isNull);
  });

  testWidgets('demo accounts fill the ID field in dev builds', (tester) async {
    await pumpApp(tester);
    await passSplash(tester);
    await tester.tap(find.text('Admin'));
    await tester.pump();
    expect(find.text('priveopapa'), findsOneWidget);
  });

  testWidgets('dark theme renders the login screen', (tester) async {
    await pumpApp(tester, brightness: Brightness.dark);
    await passSplash(tester);
    expect(find.byType(LoginScreen), findsOneWidget);
    final theme = Theme.of(tester.element(find.byType(LoginScreen)));
    expect(theme.brightness, Brightness.dark);
  });
}
