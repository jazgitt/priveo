import 'package:flutter/material.dart';

import '../cust_strings.dart';
import 'calendar_screen.dart';

/// Opens the service calendar as a page of its own, for links from other
/// screens (SKIP-06).
void openCalendarPage(BuildContext context) {
  Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => Scaffold(
        appBar: AppBar(title: const Text(CustStrings.calendarTitle)),
        body: const CalendarScreen(),
      ),
    ),
  );
}
