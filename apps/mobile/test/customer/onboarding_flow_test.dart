import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/api/api.g.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/customer/account/account_data.dart';
import 'package:priveo/features/customer/onboarding/onboarding_review_screen.dart';
import 'package:priveo/features/customer/home/customer_home_data.dart';
import 'package:priveo/l10n/app_localizations.dart';

import '../support/fakes.dart';

class _DraftApi implements HttpClientAdapter {
  final saves = <Map<String, dynamic>>[];
  bool fail = false;
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? body,
      Future<void>? cancel) async {
    saves.add((options.data as Map).cast<String, dynamic>());
    return ResponseBody.fromString(fail ? '{"code":"network","message":"Could not save"}' : '',
        fail ? 503 : 204, headers: {Headers.contentTypeHeader: [Headers.jsonContentType]});
  }
  @override
  void close({bool force = false}) {}
}

Future<FakePriveoApi> pumpReview(WidgetTester tester, _DraftApi api,
    {int step = 0, bool photo = true, bool due = true}) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final original = (onboardingJson['vehicles'] as List).first as Map;
  final data = Onboarding.fromJson({...onboardingJson, 'step': step, 'last_name': 'Mehta',
    'vehicles': [{...original, 'make': 'Hyundai', 'model': 'Creta', 'variant': 'SX', 'parking_basements': ['B2', 'P1']}]});
  final dio = Dio()..httpClientAdapter = api;
  final server = FakePriveoApi(onboardingConfirmed: false);
  final router = GoRouter(initialLocation: '/customer', routes: [
    GoRoute(path: '/customer', builder: (_, _) => Consumer(builder: (_, ref, _) =>
      ref.watch(customerHomeProvider).value?.onboardingConfirmed == true
        ? const Scaffold(body: Text('Home')) : const OnboardingReviewScreen())),
    GoRoute(path: '/customer/pay/p1', builder: (_, _) => const Scaffold(body: Text('Pay p1'))),
  ]);
  addTearDown(router.dispose);
  addTearDown(() => dio.close());
  await tester.pumpWidget(ProviderScope(overrides: [
    dioProvider.overrideWithValue(dio), apiProvider.overrideWithValue(server),
    onboardingProvider.overrideWith((ref) async => data),
    onboardingSummaryProvider.overrideWith((ref) async => [{
      'id': 'v1', 'society': 'Green Meadows', 'make': 'Hyundai', 'model': 'Creta', 'variant': 'SX',
      'payments': [if (due) {'id': 'p1', 'status': 'Due', 'amount_rupees': 999},
        {'id': 'p2', 'status': 'Received', 'amount_rupees': 1499}],
      'plan': {'list_price_rupees': 1499, 'badge': 'Founding member', 'inclusions': ['Daily clean']},
    }]),
    accountRepositoryProvider.overrideWithValue(PhotoAccount(hasPhoto: photo)),
  ], child: MaterialApp.router(routerConfig: router, theme: customerTheme, localizationsDelegates: const [
    AppLocalizations.delegate, GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  ], supportedLocales: AppLocalizations.supportedLocales)));
  await tester.pumpAndSettle();
  return server;
}

Future<void> next(WidgetTester tester) async {
  await tester.tap(find.text('Continue'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('confirmation opens the unpaid vehicle payment after saving the review', (tester) async {
    final server = await pumpReview(tester, _DraftApi(), step: 6);
    await tester.tap(find.text('Confirm & pay'));
    await tester.pumpAndSettle();
    expect(server.confirmed?.vehicles.single.id, 'v1');
    expect(find.text('Pay p1'), findsOneWidget);
  });

  testWidgets('an already received payment confirms directly to Home', (tester) async {
    final server = await pumpReview(tester, _DraftApi(), step: 6, due: false);
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    expect(server.confirmed, isNotNull);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Pay p1'), findsNothing);
  });

  testWidgets('Back retains edits saved on Continue', (tester) async {
    final api = _DraftApi();
    await pumpReview(tester, api);
    await tester.enterText(find.byType(TextField).first, 'Saved');
    await next(tester);
    await tester.tap(find.text('Back'));
    await tester.pumpAndSettle();
    expect(find.text('Saved'), findsOneWidget);
    expect(api.saves.single['first_name'], 'Saved');
  });
  testWidgets('seven review steps save on Continue and put plan before preferences', (tester) async {
    final api = _DraftApi();
    await pumpReview(tester, api);
    expect(find.text('Step 1 of 7'), findsOneWidget);
    await tester.enterText(find.byType(TextField).first, 'Updated');
    await next(tester);
    expect(api.saves.first['first_name'], 'Updated');
    expect(api.saves.first['step'], 1);
    await next(tester); // Society -> vehicle.
    expect(find.text('Hyundai Creta SX'), findsOneWidget);
    await next(tester); // Vehicle -> parking.
    expect(find.text('Your spot: B2 · 14'), findsOneWidget);
    await next(tester); // Parking -> plan.
    expect(find.text('Step 5 of 7'), findsOneWidget);
    expect(find.text('• Daily clean'), findsOneWidget);
    expect(find.text('Service cutoff time'), findsNothing);
    await next(tester); // Plan -> preferences.
    expect(find.text('Service cutoff time'), findsOneWidget);
    await next(tester); // Preferences -> review.
    expect(find.text('Step 7 of 7'), findsOneWidget);
    expect(find.textContaining('₹999'), findsWidgets);
    expect(find.text('Payable today · GST included'), findsOneWidget);
    expect(api.saves.last['step'], 6);
  });

  testWidgets('restored position opens the saved step and keeps read-only fields', (tester) async {
    await pumpReview(tester, _DraftApi(), step: 4);
    expect(find.text('Step 5 of 7'), findsOneWidget);
    expect(find.text('• Daily clean'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('a failed draft save stays on the current step', (tester) async {
    await pumpReview(tester, _DraftApi()..fail = true);
    await next(tester);
    expect(find.text('Step 1 of 7'), findsOneWidget);
    expect(find.text('Could not save'), findsOneWidget);
  });

  testWidgets('vehicle step cannot continue without its photo', (tester) async {
    await pumpReview(tester, _DraftApi(), step: 2, photo: false);
    await next(tester);
    expect(find.text('Step 3 of 7'), findsOneWidget);
    expect(find.text('Add a photo of your car to continue.'), findsOneWidget);
  });
}
