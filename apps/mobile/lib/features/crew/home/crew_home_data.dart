import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/crew_repository.dart';

/// The day the crew home shows. Null means "all scheduled so far"
/// (CRW-SCH-06).
class CrewDayNotifier extends Notifier<DateTime?> {
  @override
  DateTime? build() => _today();

  static DateTime _today() {
    final n = DateTime.now();
    return DateTime(n.year, n.month, n.day);
  }

  void shift(int days) {
    final d = state ?? _today();
    state = DateTime(d.year, d.month, d.day + days);
  }

  void today() => state = _today();
  void all() => state = null;
}

final crewDayProvider =
    NotifierProvider<CrewDayNotifier, DateTime?>(CrewDayNotifier.new);

/// The key for [crewVisitsProvider] for a day.
String visitsKey(DateTime? day) => day == null ? 'all' : apiDate(day);
