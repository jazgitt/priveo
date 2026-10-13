import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/crew/capture/media_capture.dart';
import 'package:priveo/features/crew/crew_providers.dart';
import 'package:priveo/features/customer/account/account_data.dart';
import 'package:priveo/features/customer/account/account_strings.dart';
import 'package:priveo/features/customer/vehicles/add_vehicle_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';

class Uploads extends Fake implements AccountRepository {
  String? subject;
  @override
  Future<UploadedFile> upload({
    required String purpose,
    required CapturedFile file,
    String? vehicleId,
  }) async {
    subject = vehicleId;
    return const UploadedFile(id: 'photo1', url: 'https://test/photo.png');
  }
}

class Capture extends Fake implements MediaCapture {
  @override
  Future<CapturedFile?> photo({required bool camera}) async =>
      const CapturedFile(
        path: '/fake/car.jpg',
        contentType: 'image/jpeg',
        sizeBytes: 5,
        video: false,
      );
}

class Adapter implements HttpClientAdapter {
  Map<String, dynamic>? submitted;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path == '/v1/customer/vehicles') {
      submitted = (options.data as Map).cast<String, dynamic>();
      return ResponseBody.fromString(
        jsonEncode({'id': 'v1', 'payment_id': 'p1'}),
        201,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
    }
    return ResponseBody.fromString('{}', 404);
  }

  @override
  void close({bool force = false}) {}
}

Future<void> app(
  WidgetTester tester,
  Adapter adapter, {
  bool empty = false,
}) async {
  tester.view.physicalSize = const Size(800, 2200);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  final directory = VehicleDirectory(
    empty
        ? []
        : [
            {
              'id': 's2',
              'name': 'Second society',
              'sector': 'Sector 1',
              'city': 'Gurugram',
              'cars_serviced': 2,
              'parking_basements': ['B1', 'B2'],
            },
          ],
    [
      {
        'id': 'cat1',
        'make': 'Tata',
        'model': 'Nexon',
        'variant': 'Pure',
        'category': 'Compact SUV',
      },
    ],
    [
      {
        'id': 'plan1',
        'name': 'Premium',
        'monthly_price_rupees': 999,
        'list_price_rupees': 1499,
        'includes_interior': true,
        'badge': 'Founding member',
        'inclusions': ['Daily exterior', 'Weekly interior'],
      },
    ],
  );
  final dio = Dio(BaseOptions(baseUrl: 'https://api.test'))
    ..httpClientAdapter = adapter;
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (context, _) => Scaffold(
          body: TextButton(
            onPressed: () => context.push('/add'),
            child: const Text('Open Add vehicle'),
          ),
        ),
      ),
      GoRoute(path: '/add', builder: (_, _) => const AddVehicleScreen()),
      GoRoute(
        path: '/customer/pay/:id',
        builder: (_, state) =>
            Scaffold(body: Text('Pay ${state.pathParameters['id']}')),
      ),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        dioProvider.overrideWithValue(dio),
        vehicleDirectoryProvider.overrideWith((ref) async => directory),
        accountRepositoryProvider.overrideWithValue(Uploads()),
        mediaCaptureProvider.overrideWithValue(Capture()),
      ],
      child: MaterialApp.router(
        routerConfig: router,
        theme: customerTheme,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );
  await tester.pumpAndSettle();
  await tester.tap(find.text('Open Add vehicle'));
  await tester.pumpAndSettle();
}

Future<void> next(WidgetTester tester, [String label = 'Continue']) async {
  await tester.ensureVisible(find.text(label));
  await tester.tap(find.text(label));
  await tester.pumpAndSettle();
}

Future<void> choose(
  WidgetTester tester,
  String label,
  String value, [
  String current = '',
]) async {
  final field = find.byKey(ValueKey('$label:$current'));
  await tester.ensureVisible(field);
  await tester.tap(field);
  await tester.pumpAndSettle();
  await tester.tap(find.text(value).last);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'adds a vehicle in a chosen society, requires a photo and opens its first payment',
    (tester) async {
      final adapter = Adapter();
      await app(tester, adapter);
      await tester.tap(find.text('Second society'));
      await next(tester);
      await choose(tester, 'Make', 'Tata');
      await choose(tester, 'Model', 'Nexon');
      await choose(tester, 'Variant', 'Pure');
      await tester.enterText(find.byType(TextField), 'hr01zz1234');
      expect(find.text('HR01ZZ1234'), findsOneWidget);
      await next(tester);
      expect(
        find.text('Complete the required details before continuing.'),
        findsOneWidget,
      );
      await tester.tap(find.text('Add vehicle photo (required)'));
      await tester.pumpAndSettle();
      await tester.tap(find.text(AccountStrings.fromGallery));
      await tester.pumpAndSettle();
      await next(tester);
      await choose(tester, 'Basement', 'B2');
      await tester.enterText(find.byType(TextField), '17');
      await next(tester);
      await tester.tap(find.text('Premium · ₹999/month'));
      await next(tester);
      await choose(tester, 'Interior care day', 'Monday');
      await next(tester);
      expect(find.text('Priveo will confirm the start date.'), findsOneWidget);
      await next(tester, 'Confirm & pay');
      expect(adapter.submitted, containsPair('society_id', 's2'));
      expect(adapter.submitted, containsPair('photo_upload_id', 'photo1'));
      expect(adapter.submitted, containsPair('plan_id', 'plan1'));
      expect(adapter.submitted, isNot(contains('first_payment_status')));
      expect(find.text('Pay p1'), findsOneWidget);
    },
  );
  testWidgets(
    'empty societies block adding a vehicle and explain availability',
    (tester) async {
      final adapter = Adapter();
      await app(tester, adapter, empty: true);
      expect(
        find.text('No serviced societies available at the moment.'),
        findsOneWidget,
      );
      await next(tester);
      expect(adapter.submitted, isNull);
    },
  );
}
