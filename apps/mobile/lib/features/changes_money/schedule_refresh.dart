import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../customer/data/customer_reads_repository.dart';
import '../customer/home/customer_home_data.dart';
import 'data/money_repository.dart';

/// After a skip, un-skip, pause or end of a pause, every screen that shows
/// the schedule loads again so the status is the same everywhere: the Skip
/// screen, the Pause screen, the service calendar, Home's next service and
/// My subscription (a pause moves the renewal date). The reloads are silent:
/// each screen keeps its data on screen until the new data arrives.
void refreshAfterScheduleChange(WidgetRef ref) {
  ref.invalidate(upcomingProvider);
  ref.invalidate(changesProvider);
  ref.invalidate(calendarMonthProvider);
  ref.invalidate(nextServicesProvider);
  ref.invalidate(subscriptionProvider);
  ref.invalidate(customerHomeProvider);
}
