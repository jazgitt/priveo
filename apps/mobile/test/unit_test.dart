import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/api/api.g.dart';
import 'package:priveo/core/auth/session.dart';
import 'package:priveo/core/routing/router.dart';
import 'package:priveo/core/util/format.dart';

import 'support/fakes.dart';

void main() {
  group('formatting', () {
    test('dates are dd-Mon-yy', () {
      expect(formatDate(DateTime(2026, 11, 7)), '07-Nov-26');
    });
    test('rupees use Indian grouping', () {
      expect(formatRupees(1499), '₹1,499');
      expect(formatRupees(123456), '₹1,23,456');
    });
  });

  group('Session', () {
    test('round-trips through JSON', () {
      final back = Session.fromLoginJson(crewSession.toJson());
      expect(back.role, Role.crew);
      expect(back.accessToken, 'a-crew');
    });
    test('unknown role falls back to customer, home path follows role', () {
      expect(Role.parse('nope'), Role.customer);
      expect(Role.admin.homePath, '/admin');
    });
    test('memory store keeps and clears a session', () async {
      final s = MemorySessionStore();
      await s.write(adminSession);
      expect((await s.read())?.role, Role.admin);
      await s.clear();
      expect(await s.read(), isNull);
    });
  });

  group('redirectFor', () {
    test('signed-out user goes to login', () {
      expect(redirectFor('/customer', null), '/login');
      expect(redirectFor('/login', null), isNull);
    });
    test('signed-in user is kept in their own role shell', () {
      expect(redirectFor('/login', crewSession), '/crew');
      expect(redirectFor('/admin', crewSession), '/crew');
      expect(redirectFor('/crew', crewSession), isNull);
      expect(redirectFor('/crew/profile', crewSession), isNull);
      expect(redirectFor('/customer/vehicles', crewSession), '/crew');
    });
    test('the splash is never redirected', () {
      expect(redirectFor('/splash', null), isNull);
    });
  });

  group('mappers', () {
    test('customer home', () {
      final h = CustomerHome.fromJson(customerJson);
      expect(h.vehicles.first.registration, 'MH 12 AB 1234');
      expect(h.vehicles.first.nextService?.date, DateTime(2026, 11, 7));
      expect(h.vehicles.last.subscriptionStatus, isNull);
      // What may be empty is sent back as empty.
      expect(h.vehicles.last.toJson()['next_service'], isNull);
      expect(h.vehicles.first.toJson()['next_service'],
          {'date': '2026-11-07', 'service': 'Cleaning-External', 'status': 'Scheduled'});
      expect(h.quickActions, hasLength(4));
    });
    test('crew home', () {
      final h = CrewHome.fromJson(crewJson);
      expect(h.jobs.first.vehicle, 'MH 12 AB 1234');
      expect(h.done + h.left, h.total);
    });
  });
}
