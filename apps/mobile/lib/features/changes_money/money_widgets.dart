import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../core/network/api_failure.dart';
import '../../core/ui/widgets.dart';
import 'data/money_models.dart';
import 'strings.dart';

/// What the customer reads for a payment status (PAY-09): Not Due, Due, Due
/// today, Over due, Initiated or Paid. The backend sets it; the app displays it.
String paymentStatusLabel(PaymentDto p) => paymentStatusText(p.status);

String paymentStatusText(String status) => switch (status) {
      'Not Due' => MoneyStrings.statusNotDue,
      'Due' => MoneyStrings.statusDue,
      'Due today' => MoneyStrings.statusDueToday,
      'Over due' => MoneyStrings.statusOverdue,
      'Initiated' => MoneyStrings.statusInitiated,
      'Paid' => MoneyStrings.statusPaid,
      final other => other,
    };

ChipTone paymentTone(String status) => switch (status) {
      'Paid' => ChipTone.ok,
      'Initiated' => ChipTone.info,
      'Due' || 'Due today' || 'Over due' => ChipTone.warn,
      _ => ChipTone.neutral,
    };

class PaymentStatusChip extends StatelessWidget {
  const PaymentStatusChip(this.payment, {super.key});

  final PaymentDto payment;

  @override
  Widget build(BuildContext context) =>
      StatusChip(paymentStatusLabel(payment), tone: paymentTone(payment.status));
}

/// The status message under a payment ("Due in 3 days", "2 days over due"),
/// and "Your last payment failed" after a rejection (PAY-17).
class PaymentStatusNote extends StatelessWidget {
  const PaymentStatusNote({
    super.key,
    required this.message,
    required this.lastPaymentFailed,
  });

  final String message;
  final bool lastPaymentFailed;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final small = Theme.of(context).textTheme.bodySmall;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (message.isNotEmpty) Text(message, style: small),
        if (lastPaymentFailed)
          Text(MoneyStrings.lastPaymentFailed,
              style: small?.copyWith(color: scheme.error)),
      ],
    );
  }
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
