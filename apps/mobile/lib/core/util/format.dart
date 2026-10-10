import 'package:intl/intl.dart';

final _date = DateFormat('dd-MMM-yy');

/// Dates in the app are `dd-Mon-yy`, for example `07-Nov-26`.
String formatDate(DateTime d) => _date.format(d);

/// Reads a `yyyy-mm-dd` date from the API.
DateTime parseApiDate(String s) => DateTime.parse(s);

/// Rupees, GST included. The API sends whole rupees in Phase 0.
String formatRupees(int rupees) => '₹${NumberFormat.decimalPattern('en_IN').format(rupees)}';

final _clock = DateFormat('h:mm a');

/// A time of day from the API (`HH:MM`) as `6:30 AM`.
String formatClock(String hhmm) {
  final parts = hhmm.split(':');
  return _clock.format(DateTime(2000, 1, 1, int.parse(parts[0]), int.parse(parts[1])));
}
