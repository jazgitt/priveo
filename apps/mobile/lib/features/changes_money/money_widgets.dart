import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../core/network/api_failure.dart';
import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/money_models.dart';
import 'strings.dart';

/// What the customer reads for a payment status (PAY-09): "Due by 07-Nov-26",
/// Over due, Initiated or Received. The backend sets it; the app displays it.
String paymentStatusLabel(PaymentDto p) => switch (p.status) {
      'Due' => MoneyStrings.statusDue(formatDate(p.dueDate)),
      'Over due' => MoneyStrings.statusOverdue,
      'Initiated' => MoneyStrings.statusInitiated,
      'Received' => MoneyStrings.statusReceived,
      final other => other,
    };

ChipTone paymentTone(String status) => switch (status) {
      'Received' => ChipTone.ok,
      'Initiated' => ChipTone.info,
      'Over due' => ChipTone.warn,
      _ => ChipTone.neutral,
    };

class PaymentStatusChip extends StatelessWidget {
  const PaymentStatusChip(this.payment, {super.key});

  final PaymentDto payment;

  @override
  Widget build(BuildContext context) =>
      StatusChip(paymentStatusLabel(payment), tone: paymentTone(payment.status));
}

/// The text to show for a failed call: the server's own message, which says
/// what went wrong (for example that 9 PM has passed), or the network text.
String failureText(Object error) {
  if (error is DioException) return failureText(ApiFailure.fromDio(error));
  if (error is ApiFailure) {
    return error.message ??
        'We could not reach the server. Check your connection and try again.';
  }
  return 'Something went wrong. Please try again.';
}

void showFailure(BuildContext context, Object error) {
  ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(failureText(error))));
}

void showMessage(BuildContext context, String text) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
}

/// Half-hour steps of the day, as `HH:MM` (ADD-04).
List<String> halfHourSteps() => [
      for (var h = 0; h < 24; h++)
        for (final m in const [0, 30])
          '${h.toString().padLeft(2, '0')}:${m.toString().padLeft(2, '0')}'
    ];
