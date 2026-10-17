// The customer's account, profile, vehicle photo and complaint photos
// (ACC-01, ACC-06, ACC-08, VEH-01, VEH-04, ONB-22, ISS-02, ISS-04).
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/crew/capture/media_capture.dart';
import 'package:priveo/features/crew/crew_providers.dart'
    show mediaCaptureProvider;
import 'package:priveo/features/customer/account/account_data.dart';
import 'package:priveo/features/customer/account/photo_widgets.dart';
import 'package:priveo/features/customer/account/profile_screens.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/customer/home/vehicle_header.dart';
import 'package:priveo/features/support/data/support_repository.dart';
import 'package:priveo/features/support/report_issue_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';

import '../support/fakes.dart' show FakePriveoApi;
import '../support/support_fakes.dart';
import 'customer_slice_test.dart' show FakeReads;

class FakeAccount implements AccountRepository {
  ProfileDto current = const ProfileDto(
    firstName: 'Asha',
    lastName: 'Rao',
    email: 'asha@example.com',
    mobile: '9876543210',
    society: 'DLF Meadows',
    flat: 'A-101',
    initials: 'AR',
  );
  final uploads = <String>[];
  final edits = <Map<String, String>>[];
  final emailCalls = <String>[];
  String? vehiclePhoto;

  @override
  Future<ProfileDto> profile() async => current;

  @override
  Future<ProfileDto> editProfile({
    required String firstName,
    required String lastName,
    required String mobile,
  }) async {
    edits.add({'first': firstName, 'last': lastName, 'mobile': mobile});
    return current;
  }

  @override
  Future<void> startEmailChange(String email) async =>
      emailCalls.add('start:$email');

  @override
  Future<ProfileDto> verifyEmail(String code) async {
    emailCalls.add('verify:$code');
    return current;
  }

  @override
  Future<void> changePassword({
    required String current,
    required String next,
  }) async {}

  @override
  Future<VehicleAccountDto> vehicleAccount(String vehicleId) async =>
      VehicleAccountDto(
        id: vehicleId,
        parkingBasement: 'B2',
        parkingNumber: '14',
        photoUrl: vehiclePhoto,
        rcStatus: 'Not uploaded',
      );

  @override
  Future<VehicleAccountDto> editParking(
    String vehicleId, {
    String? basement,
    String? number,
  }) async => vehicleAccount(vehicleId);

  @override
  Future<UploadedFile> upload({
    required String purpose,
    required CapturedFile file,
    String? vehicleId,
  }) async {
    uploads.add('$purpose:${vehicleId ?? ''}:${file.contentType}');
    return UploadedFile(id: 'u-${uploads.length}', url: 'https://m.test/p.jpg');
  }
}

class _Capture implements MediaCapture {
  _Capture([this.file]);

  CapturedFile? file;

  @override
  Future<CapturedFile?> photo({required bool camera}) async =>
      file ??
      const CapturedFile(
        path: '/tmp/a.jpg',
        contentType: 'image/jpeg',
        sizeBytes: 2048,
        video: false,
      );

  @override
  Future<CapturedFile?> video({required bool camera}) async => null;
}

/// Reads with nothing in them: the screens under test do not need them.
class _NoReads implements CustomerReadsRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      Future<dynamic>.value(invocation.memberName == #vehicles
          ? <VehicleSummaryDto>[]
          : <HistoryItemDto>[]);
}

Widget _app(
  Widget home,
  FakeAccount account, {
  _Capture? capture,
  SupportRepository? support,
  GoRouter? router,
  List<Override> extra = const [],
}) {
  final overrides = [
    accountRepositoryProvider.overrideWithValue(account),
    mediaCaptureProvider.overrideWithValue(capture ?? _Capture()),
    customerReadsProvider.overrideWithValue(_NoReads()),
    if (support != null) supportRepositoryProvider.overrideWithValue(support),
    ...extra,
  ];
  const delegates = [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ];
  return ProviderScope(
    retry: (_, _) => null,
    overrides: overrides,
    child: router != null
        ? MaterialApp.router(
            theme: customerTheme,
            routerConfig: router,
            localizationsDelegates: delegates,
            supportedLocales: AppLocalizations.supportedLocales,
          )
        : MaterialApp(
            theme: customerTheme,
            localizationsDelegates: delegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(body: home),
          ),
  );
}

void _tall(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
}

void main() {
  testWidgets('edit profile saves names and mobile (ACC-06)', (tester) async {
    _tall(tester);
    final account = FakeAccount();
    await tester.pumpWidget(_app(const EditProfileScreen(), account));
    await tester.pumpAndSettle();
    expect(find.text('asha@example.com'), findsOneWidget);
    await tester.enterText(find.widgetWithText(TextField, 'First name'), 'Asha2');
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    // A digit in a name is refused and nothing is sent.
    expect(
      find.text('Enter your first name, using letters only.'),
      findsOneWidget,
    );
    expect(account.edits, isEmpty);
    await tester.enterText(find.widgetWithText(TextField, 'First name'), 'Ashu');
    await tester.enterText(
      find.widgetWithText(TextField, 'Mobile number'),
      '123',
    );
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(find.text('Enter a 10-digit mobile number.'), findsOneWidget);
    await tester.enterText(
      find.widgetWithText(TextField, 'Mobile number'),
      '9000000009',
    );
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(account.edits, [
      {'first': 'Ashu', 'last': 'Rao', 'mobile': '9000000009'},
    ]);
  });

  testWidgets('change email asks for the code, then verifies (ACC-08)', (
    tester,
  ) async {
    _tall(tester);
    final account = FakeAccount();
    await tester.pumpWidget(_app(const ChangeEmailScreen(), account));
    await tester.enterText(find.byType(TextField), 'not-an-email');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(find.text('Enter a valid email.'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'new@example.com');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(account.emailCalls, ['start:new@example.com']);
    await tester.enterText(find.widgetWithText(TextField, '6-digit code'), '123456');
    await tester.tap(find.text('Verify email'));
    await tester.pumpAndSettle();
    expect(account.emailCalls.last, 'verify:123456');
  });

  testWidgets('the vehicle photo is added through the camera (VEH-01)', (
    tester,
  ) async {
    _tall(tester);
    final account = FakeAccount();
    await tester.pumpWidget(
      _app(const VehiclePhotoField(vehicleId: 'v1', reportDone: true), account),
    );
    await tester.pumpAndSettle();
    expect(find.text('Add a photo of your car'), findsOneWidget);
    await tester.tap(find.text('Add a photo of your car'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo'));
    await tester.pumpAndSettle();
    expect(account.uploads, ['vehicle:v1:image/jpeg']);
    expect(find.text('Change photo'), findsOneWidget);
  });

  testWidgets('a photo in a format that is not accepted is refused', (
    tester,
  ) async {
    _tall(tester);
    final account = FakeAccount();
    final capture = _Capture(
      const CapturedFile(
        path: '/tmp/a.gif',
        contentType: null,
        sizeBytes: 100,
        video: false,
      ),
    );
    await tester.pumpWidget(
      _app(const VehiclePhotoField(vehicleId: 'v1'), account, capture: capture),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Add a photo of your car'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Choose from gallery'));
    await tester.pumpAndSettle();
    expect(find.text('This file format is not accepted.'), findsOneWidget);
    expect(account.uploads, isEmpty);
  });

  testWidgets('report an issue names the vehicle and links its latest visit', (
    tester,
  ) async {
    _tall(tester);
    await tester.pumpWidget(
      _app(
        const ReportIssueScreen(),
        FakeAccount(),
        support: FakeSupportRepository(),
        extra: [
          apiProvider.overrideWithValue(FakePriveoApi()),
          customerReadsProvider.overrideWithValue(FakeReads()),
        ],
      ),
    );
    await tester.pumpAndSettle();
    // The header names the selected vehicle.
    expect(
      find.descendant(
        of: find.byType(VehicleHeader),
        matching: find.text('MH 12 AB 1234'),
      ),
      findsOneWidget,
    );
    // The linked visit starts as that vehicle's latest visit (03-Nov-26).
    expect(find.textContaining('03-Nov-26'), findsOneWidget);
  });

  testWidgets('report an issue sends the attached photos and the visit', (
    tester,
  ) async {
    _tall(tester);
    final account = FakeAccount();
    final support = FakeSupportRepository();
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) => const ReportIssueScreen(visitId: 'visit-7'),
        ),
        GoRoute(
          path: '/customer/support/complaints',
          builder: (_, _) => const Scaffold(body: Text('complaints page')),
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      _app(const SizedBox(), account, support: support, router: router),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cleaning quality'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Describe what happened'),
      'Streaks',
    );
    await tester.ensureVisible(find.text('Add a photo'));
    await tester.tap(find.text('Add a photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo'));
    await tester.pumpAndSettle();
    expect(account.uploads, ['complaint::image/jpeg']);
    await tester.ensureVisible(find.text('Send report'));
    await tester.tap(find.text('Send report'));
    await tester.pumpAndSettle();
    expect(support.created.single['photoKeys'], ['u-1']);
    expect(support.created.single['visitId'], 'visit-7');
    expect(find.text('complaints page'), findsOneWidget);
  });
}
