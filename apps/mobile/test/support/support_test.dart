// The support screens: help, report an issue, my complaints, feedback and
// rating, monthly check-in, crew ratings and the admin's alert list.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/admin_quick/alerts/alerts_data.dart';
import 'package:priveo/features/support/data/support_models.dart';
import 'package:priveo/features/support/feedback_sheet.dart';
import 'package:priveo/features/support/help_screen.dart';
import 'package:priveo/features/support/routes.dart';
import 'package:priveo/features/support/support_strings.dart';

import 'support_fakes.dart';

Finder star(int n) => find.bySemanticsLabel('Rate $n out of 5');

Future<void> tap(WidgetTester tester, Finder f) async {
  await tester.ensureVisible(f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

bool enabled(WidgetTester tester, String label) {
  final s = tester.getSemantics(find.bySemanticsLabel(label).last);
  return s.getSemanticsData().hasAction(SemanticsAction.tap);
}

void main() {
  group('help', () {
    testWidgets('lists the options and opens the dialer and WhatsApp',
        (tester) async {
      final opened = <Uri>[];
      final repo = FakeSupportRepository();
      await pumpSupport(tester,
          initial: SupportRoutes.help, repo: repo, opened: opened);
      expect(find.text('Help and support'), findsOneWidget);
      expect(find.text('Support hours: 6 AM to 10 PM'), findsOneWidget);
      expect(find.text('2 in progress'), findsOneWidget);
      // No check-in is due, so there is no tile for it.
      expect(find.text('Monthly check-in'), findsNothing);

      await tap(tester, find.text('Call support'));
      await tap(tester, find.text('WhatsApp support'));
      expect(opened.map((u) => u.toString()),
          ['tel:+911234567890', 'https://wa.me/919876543210']);
    });

    testWidgets('shows the check-in when one is due', (tester) async {
      final repo = FakeSupportRepository()
        ..pending = const [
          PendingCheckIn(
              subscriptionId: 's1',
              vehicleLabel: 'Hyundai Creta',
              cycleStart: '2026-10-08'),
        ];
      await pumpSupport(tester, initial: SupportRoutes.help, repo: repo);
      expect(find.text('Monthly check-in'), findsOneWidget);
      await tap(tester, find.text('Monthly check-in'));
      expect(find.textContaining('Hyundai Creta'), findsOneWidget);
    });

    testWidgets('give feedback opens the feedback sheet', (tester) async {
      await pumpSupport(tester, initial: SupportRoutes.help);
      await tap(tester, find.text('Give feedback'));
      expect(find.text('Your rating'), findsOneWidget);
    });

    testWidgets('a failed load shows the retry view', (tester) async {
      final repo = _Broken();
      await pumpSupport(tester, initial: SupportRoutes.help, repo: repo);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('report an issue', () {
    testWidgets('asks for a category and a description (ISS-05)',
        (tester) async {
      final repo = FakeSupportRepository();
      await pumpSupport(tester, initial: SupportRoutes.report, repo: repo);
      await tap(tester, find.text('Send report'));
      expect(find.text('Choose what went wrong.'), findsOneWidget);
      expect(find.text('Describe what happened.'), findsOneWidget);
      expect(repo.created, isEmpty);
    });

    testWidgets('sends the report and lands on My complaints (ISS-06)',
        (tester) async {
      final repo = FakeSupportRepository();
      await pumpSupport(tester,
          initial: '${SupportRoutes.report}?visit=visit-7', repo: repo);
      expect(find.text('This report is linked to the clean you came from.'),
          findsOneWidget);
      await tap(tester, find.text('Billing'));
      await tester.enterText(find.byType(TextField), 'Charged twice');
      await tap(tester, find.text('Send report'));
      expect(repo.created, [
        {
          'category': 'Billing',
          'description': 'Charged twice',
          'visitId': 'visit-7'
        }
      ]);
      expect(find.text('My complaints'), findsOneWidget);
      expect(find.text('#C-0009'), findsOneWidget);
    });

    testWidgets("shows the server's message when sending fails",
        (tester) async {
      final repo = FakeSupportRepository()..failWith = 'Please try later.';
      await pumpSupport(tester, initial: SupportRoutes.report, repo: repo);
      await tap(tester, find.text('Other'));
      await tester.enterText(find.byType(TextField), 'Hello');
      await tap(tester, find.text('Send report'));
      expect(find.text('Please try later.'), findsOneWidget);
      expect(find.text('Send report'), findsOneWidget);
    });
  });

  group('my complaints', () {
    testWidgets('lists complaints with status and the latest note',
        (tester) async {
      final repo = FakeSupportRepository()
        ..complaintList = [
          makeComplaint(
              id: 'c2',
              displayId: '#C-0002',
              status: 'In progress',
              latestNote: 'Supervisor visit booked'),
          makeComplaint(id: 'c1', status: 'Resolved'),
        ];
      await pumpSupport(tester, initial: SupportRoutes.complaints, repo: repo);
      expect(find.text('#C-0002'), findsOneWidget);
      expect(find.text('In progress'), findsOneWidget);
      expect(find.text('Resolved'), findsOneWidget);
      expect(find.text('Supervisor visit booked'), findsOneWidget);
      expect(find.text('Raised 07-Nov-26'), findsNWidgets(2));
    });

    testWidgets('says so when there are none', (tester) async {
      await pumpSupport(tester, initial: SupportRoutes.complaints);
      expect(find.text('You have not raised any complaints.'), findsOneWidget);
    });

    testWidgets('shows the thread and sends a reply', (tester) async {
      final repo = FakeSupportRepository()
        ..detail = makeComplaint(status: 'In progress', updates: [
          ThreadEntry(
              id: 'u1',
              authorRole: 'admin',
              note: 'Re-cleaned same day',
              status: 'In progress',
              createdAt: DateTime.utc(2026, 11, 7, 9)),
          ThreadEntry(
              id: 'u2',
              authorRole: 'customer',
              note: 'Thank you',
              status: null,
              createdAt: DateTime.utc(2026, 11, 7, 10)),
        ]);
      await pumpSupport(tester,
          initial: SupportRoutes.complaint('c1'), repo: repo);
      expect(find.text('Re-cleaned same day'), findsOneWidget);
      expect(find.text('Status: In progress'), findsOneWidget);
      expect(find.text('Thank you'), findsOneWidget);
      expect(find.text('Priveo'), findsOneWidget);
      expect(find.text('You'), findsOneWidget);

      await tester.enterText(find.byType(TextField), 'Looks good now');
      await tap(tester, find.text('Send'));
      expect(repo.replies, ['Looks good now']);
    });

    testWidgets('a resolved complaint has no reply box', (tester) async {
      final repo = FakeSupportRepository()
        ..detail = makeComplaint(status: 'Resolved');
      await pumpSupport(tester,
          initial: SupportRoutes.complaint('c1'), repo: repo);
      expect(find.byType(TextField), findsNothing);
      expect(
          find.text(
              'This complaint is resolved. Raise a new one if the problem is back.'),
          findsOneWidget);
    });
  });

  group('feedback', () {
    Future<FakeSupportRepository> open(WidgetTester tester) async {
      final repo = FakeSupportRepository();
      await pumpSupport(tester, initial: SupportRoutes.help, repo: repo);
      await tap(tester, find.text('Give feedback'));
      return repo;
    }

    testWidgets('Send needs a rating or a comment, not a category alone',
        (tester) async {
      final repo = await open(tester);
      expect(enabled(tester, 'Send'), isFalse);
      await tap(tester, find.text('Glass'));
      expect(find.text('Smudges or spots'), findsOneWidget);
      expect(enabled(tester, 'Send'), isFalse);
      await tap(tester, star(4));
      expect(enabled(tester, 'Send'), isTrue);
      expect(repo.feedback, isEmpty);
    });

    testWidgets('sends with the testimonial box off unless ticked',
        (tester) async {
      final repo = await open(tester);
      await tap(tester, star(5));
      await tap(tester, find.text('Send'));
      expect(repo.feedback, [
        {'category': null, 'rating': 5, 'comment': '', 'testimonial': false}
      ]);
      expect(find.text('Thank you for your feedback.'), findsOneWidget);
    });

    testWidgets('a comment alone can be sent, with permission',
        (tester) async {
      final repo = await open(tester);
      await tester.enterText(find.byType(TextField), 'Great job');
      await tester.pumpAndSettle();
      await tap(tester, find.byType(CheckboxListTile));
      await tap(tester, find.text('Send'));
      expect(repo.feedback.single['comment'], 'Great job');
      expect(repo.feedback.single['rating'], isNull);
      expect(repo.feedback.single['testimonial'], isTrue);
    });
  });

  group('visit rating', () {
    Future<FakeSupportRepository> open(WidgetTester tester) async {
      final repo = FakeSupportRepository();
      await pumpSupport(tester, initial: SupportRoutes.help, repo: repo);
      final context = tester.element(find.byType(HelpScreen));
      showVisitRatingSheet(context, 'visit-1');
      await tester.pumpAndSettle();
      return repo;
    }

    testWidgets('5 stars offers the positive tags', (tester) async {
      final repo = await open(tester);
      await tap(tester, star(5));
      expect(find.text('Spotless'), findsOneWidget);
      expect(find.text('Glass'), findsNothing);
      await tap(tester, find.text('Spotless'));
      await tap(tester, find.text('Send'));
      expect(repo.visitRatings.single, {
        'visitId': 'visit-1',
        'rating': 5,
        'tags': ['Spotless'],
        'comment': '',
        'testimonial': false,
      });
    });

    testWidgets('fewer than 5 stars offers the issue tags, and clears the rest',
        (tester) async {
      final repo = await open(tester);
      await tap(tester, star(5));
      await tap(tester, find.text('Spotless'));
      await tap(tester, star(3));
      expect(find.text('Spotless'), findsNothing);
      await tap(tester, find.text('Timing'));
      await tap(tester, find.text('Send'));
      expect(repo.visitRatings.single['tags'], ['Timing']);
      expect(repo.visitRatings.single['rating'], 3);
    });
  });

  group('monthly check-in', () {
    const due = PendingCheckIn(
        subscriptionId: 's1',
        vehicleLabel: 'Hyundai Creta',
        cycleStart: '2026-10-08');

    testWidgets('needs one rating, then saves and says thank you',
        (tester) async {
      final repo = FakeSupportRepository()..pending = [due];
      await pumpSupport(tester, initial: SupportRoutes.checkin, repo: repo);
      expect(find.text('Value for money'), findsOneWidget);
      expect(find.text('Schedule fit'), findsOneWidget);
      expect(enabled(tester, 'Submit'), isFalse);

      await tap(tester, star(4).first);
      expect(enabled(tester, 'Submit'), isTrue);
      await tester.enterText(find.byType(TextField), 'All fine');
      await tap(tester, find.text('Submit'));
      expect(repo.checkIns.single, {
        'subscriptionId': 's1',
        'ratings': {'Value for money': 4},
        'comment': 'All fine',
      });
      expect(find.text('Thank you. Your check-in is saved.'), findsOneWidget);
    });

    testWidgets('tapping the same star again leaves the category unrated',
        (tester) async {
      final repo = FakeSupportRepository()..pending = [due];
      await pumpSupport(tester, initial: SupportRoutes.checkin, repo: repo);
      await tap(tester, star(4).first);
      await tap(tester, star(4).first);
      expect(enabled(tester, 'Submit'), isFalse);
    });

    testWidgets('says so when nothing is due', (tester) async {
      await pumpSupport(tester, initial: SupportRoutes.checkin);
      expect(find.text('There is no check-in to give right now.'),
          findsOneWidget);
    });
  });

  group('admin alerts', () {
    AdminAlert alert(String id, String title, {bool read = false}) =>
        AdminAlert(
          id: id,
          kind: 'complaint_raised',
          title: title,
          body: 'Aarav: Billing',
          createdAt: DateTime.utc(2026, 11, 7, 6),
          read: read,
          refType: 'complaint',
          refId: 'c1',
        );

    testWidgets('lists alerts with the unread count and marks one read',
        (tester) async {
      final repo = FakeAlertsRepository(
          [alert('a1', 'New complaint #C-0001'), alert('a2', 'Old', read: true)]);
      await pumpSupport(tester, initial: '/admin/alerts', alertsRepo: repo);
      expect(find.text('1 unread'), findsOneWidget);
      expect(find.text('New complaint #C-0001'), findsOneWidget);

      await tap(tester, find.text('New complaint #C-0001'));
      expect(repo.readIds, ['a1']);
      expect(find.text('0 unread'), findsOneWidget);
    });

    testWidgets('marks all as read', (tester) async {
      final repo =
          FakeAlertsRepository([alert('a1', 'One'), alert('a2', 'Two')]);
      await pumpSupport(tester, initial: '/admin/alerts', alertsRepo: repo);
      await tap(tester, find.text('Mark all as read'));
      expect(repo.readAllCalls, 1);
      expect(find.text('0 unread'), findsOneWidget);
      expect(find.text('Mark all as read'), findsNothing);
    });

    testWidgets('says so when there are none', (tester) async {
      await pumpSupport(tester, initial: '/admin/alerts');
      expect(find.text('No alerts.'), findsOneWidget);
    });
  });

  group('units', () {
    test('the ARB fragment has the same keys and words as the code', () {
      final arb = jsonDecode(
              File('lib/l10n/fragments/support.arb').readAsStringSync())
          as Map<String, dynamic>;
      final words = {
        for (final e in arb.entries)
          if (!e.key.startsWith('@')) e.key: e.value
      };
      expect(words, SupportText.all);
      expect(words.keys.every((k) => k.startsWith('support_')), isTrue);
    });

    test('complaint JSON and progress step', () {
      final c = Complaint.fromJson({
        'id': 'x',
        'display_id': '#C-0003',
        'category': 'Billing',
        'description': 'd',
        'status': 'In progress',
        'created_at': '2026-11-07T06:00:00Z',
        'latest_note': null,
        'updates': [
          {
            'id': 'u',
            'author_role': 'customer',
            'note': 'hi',
            'status': null,
            'created_at': '2026-11-07T07:00:00Z'
          }
        ],
      });
      expect(c.step, 2);
      expect(c.updates.single.fromCustomer, isTrue);
      expect(makeComplaint(status: 'Raised').step, 1);
      expect(makeComplaint(status: 'Resolved').step, 3);
    });

    test('whatsapp link keeps only the digits', () {
      expect(whatsappUri('+91 98765-43210').toString(),
          'https://wa.me/919876543210');
    });

  });
}

/// Every read fails, as when the phone is offline.
class _Broken extends FakeSupportRepository {
  @override
  Future<SupportContact> contact() async => throw Exception('offline');
}
