import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/admin_quick/alerts/alerts_data.dart';
import 'package:priveo/features/admin_quick/alerts/routes.dart' as alerts;
import 'package:priveo/features/support/data/support_models.dart';
import 'package:priveo/features/support/data/support_repository.dart';
import 'package:priveo/features/support/routes.dart' as support;
import 'package:priveo/features/support/widgets.dart';
import 'package:priveo/l10n/app_localizations.dart';

Complaint makeComplaint({
  String id = 'c1',
  String displayId = '#C-0001',
  String status = 'Raised',
  String description = 'Streaks on the glass',
  String? latestNote,
  List<ThreadEntry> updates = const [],
}) =>
    Complaint(
      id: id,
      displayId: displayId,
      category: 'Cleaning quality',
      description: description,
      status: status,
      createdAt: DateTime.utc(2026, 11, 7, 6),
      latestNote: latestNote,
      updates: updates,
    );

const sampleOptions = SupportOptions(
  issueCategories: [
    'Cleaning quality',
    'Missed service',
    'Damage concern',
    'Crew behaviour',
    'Billing',
    'Other',
  ],
  feedbackCategories: [
    OptionItem(id: 'f1', name: 'Glass', description: 'Smudges or spots'),
    OptionItem(id: 'f2', name: 'Timing', description: 'Not finished by cutoff'),
  ],
  positiveTags: [
    OptionItem(id: 'p1', name: 'Spotless'),
    OptionItem(id: 'p2', name: 'On time'),
  ],
  checkinCategories: [
    OptionItem(id: 'k1', name: 'Value for money', description: 'Good value?'),
    OptionItem(id: 'k2', name: 'Schedule fit'),
  ],
);

class FakeSupportRepository implements SupportRepository {
  SupportContact contactValue = const SupportContact(
    helpline: '+911234567890',
    whatsapp: '+91 98765 43210',
    hours: '6 AM to 10 PM',
    complaintsInProgress: 2,
  );
  List<Complaint> complaintList = [];
  Complaint? detail;
  List<PendingCheckIn> pending = [];
  CrewRatings ratings = const CrewRatings(
    periodDays: 30,
    count: 4,
    average: 4.5,
    stars: {1: 0, 2: 0, 3: 0, 4: 2, 5: 2},
  );

  /// When set, the next write fails with this message.
  String? failWith;

  final created = <Map<String, Object?>>[];
  final replies = <String>[];
  final feedback = <Map<String, Object?>>[];
  final visitRatings = <Map<String, Object?>>[];
  final checkIns = <Map<String, Object?>>[];

  void _maybeFail() {
    final m = failWith;
    if (m != null) {
      failWith = null;
      throw ApiFailure(code: 'error', message: m, statusCode: 422);
    }
  }

  @override
  Future<SupportContact> contact() async => contactValue;

  @override
  Future<SupportOptions> options() async => options_;

  SupportOptions options_ = sampleOptions;

  @override
  Future<Complaint> createComplaint({
    required String category,
    required String description,
    String? visitId,
    List<String> photoKeys = const [],
  }) async {
    _maybeFail();
    created.add({
      'category': category,
      'description': description,
      'visitId': visitId,
      if (photoKeys.isNotEmpty) 'photoKeys': photoKeys,
    });
    final c = makeComplaint(
        id: 'new', displayId: '#C-0009', description: description);
    complaintList = [c, ...complaintList];
    return c;
  }

  @override
  Future<List<Complaint>> complaints() async => complaintList;

  @override
  Future<Complaint> complaint(String id) async => detail!;

  @override
  Future<Complaint> reply(String id, String note) async {
    _maybeFail();
    replies.add(note);
    return detail!;
  }

  @override
  Future<void> sendFeedback({
    String? category,
    int? rating,
    String comment = '',
    bool testimonial = false,
  }) async {
    _maybeFail();
    feedback.add({
      'category': category,
      'rating': rating,
      'comment': comment,
      'testimonial': testimonial,
    });
  }

  @override
  Future<void> rateVisit(
    String visitId, {
    required int rating,
    List<String> tags = const [],
    String comment = '',
    bool testimonial = false,
  }) async {
    _maybeFail();
    visitRatings.add({
      'visitId': visitId,
      'rating': rating,
      'tags': tags,
      'comment': comment,
      'testimonial': testimonial,
    });
  }

  @override
  Future<List<PendingCheckIn>> pendingCheckIns() async => pending;

  @override
  Future<void> submitCheckIn(
      String subscriptionId, Map<String, int> ratings, String comment) async {
    _maybeFail();
    checkIns.add({
      'subscriptionId': subscriptionId,
      'ratings': ratings,
      'comment': comment,
    });
    pending = [];
  }

  @override
  Future<CrewRatings> crewRatings() async => ratings;
}

class FakeAlertsRepository implements AlertsRepository {
  FakeAlertsRepository(this.items);

  List<AdminAlert> items;
  final readIds = <String>[];
  int readAllCalls = 0;

  @override
  Future<AlertList> list() async => AlertList(
      unreadCount: items.where((a) => !a.read).length, items: items);

  @override
  Future<void> markRead(String id) async {
    readIds.add(id);
    items = [
      for (final a in items)
        a.id == id ? _asRead(a) : a,
    ];
  }

  @override
  Future<void> markAllRead() async {
    readAllCalls++;
    items = [for (final a in items) _asRead(a)];
  }

  static AdminAlert _asRead(AdminAlert a) => AdminAlert(
        id: a.id,
        kind: a.kind,
        title: a.title,
        body: a.body,
        createdAt: a.createdAt,
        read: true,
        refType: a.refType,
        refId: a.refId,
      );
}

/// Opens [initial] with the support and alert routes, on fake data.
Future<void> pumpSupport(
  WidgetTester tester, {
  required String initial,
  SupportRepository? repo,
  AlertsRepository? alertsRepo,
  List<Uri>? opened,
  bool tall = true,
}) async {
  if (tall) {
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 2;
    addTearDown(tester.view.reset);
  }
  final router = GoRouter(
    initialLocation: initial,
    routes: [...support.routes, ...alerts.routes],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(ProviderScope(
    overrides: [
      supportRepositoryProvider
          .overrideWithValue(repo ?? FakeSupportRepository()),
      alertsRepositoryProvider
          .overrideWithValue(alertsRepo ?? FakeAlertsRepository([])),
      linkOpenerProvider.overrideWithValue((uri) async {
        opened?.add(uri);
        return true;
      }),
    ],
    child: MaterialApp.router(
      theme: customerTheme,
      routerConfig: router,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
    ),
  ));
  await tester.pumpAndSettle();
}
