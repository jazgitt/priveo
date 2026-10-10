import 'package:intl/intl.dart';

final _date = DateFormat('dd-MMM-yy');

/// Dates in the app are `dd-Mon-yy`, for example `07-Nov-26`.
String formatDate(DateTime d) => _date.format(d);

/// Reads a `yyyy-mm-dd` date from the API.
DateTime parseApiDate(String s) => DateTime.parse(s);

/// Rupees, GST included. The API sends whole rupees in Phase 0.
String formatRupees(int rupees) => '₹${NumberFormat.decimalPattern('en_IN').format(rupees)}';
