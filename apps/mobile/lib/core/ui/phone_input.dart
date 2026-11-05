import 'package:flutter/services.dart';

/// Phone entry rule (owner, 5-Nov-26): digits only, at most 10 of them.
final List<TextInputFormatter> mobileFormatters = [
  FilteringTextInputFormatter.digitsOnly,
  LengthLimitingTextInputFormatter(10),
];
