import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import '../support/widgets.dart' show linkOpenerProvider;
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart' show failureText;
import 'strings.dart';

/// The invoice for one payment (SUB-12): a formatted page the customer can
/// copy or email to themselves. A PDF and a share sheet need new packages.
class InvoiceScreen extends ConsumerWidget {
  const InvoiceScreen({super.key, required this.paymentId});

  final String paymentId;

  /// The invoice as plain text, for the clipboard and the email body.
  static String asText(InvoiceDto inv) => [
    '${MoneyStrings.invoiceTitle} ${inv.number}',
    'Date: ${formatDate(inv.issuedOn)}',
    inv.description,
    'Amount: ${formatRupees(inv.amountRupees)} (${MoneyStrings.gstIncluded})',
    'Billed to: ${inv.customerName}',
    'Seller: ${inv.sellerName}, GSTIN ${inv.sellerGstin}',
  ].join('\n');

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final invoice = ref.watch(_invoiceProvider(paymentId));
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.invoiceTitle)),
      body: invoice.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(_invoiceProvider(paymentId)),
        ),
        data: (inv) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(inv.number, style: text.titleMedium),
                  Text(formatDate(inv.issuedOn)),
                  const SizedBox(height: 12),
                  Text(inv.description),
                  Text(
                    formatRupees(inv.amountRupees),
                    style: text.headlineSmall,
                  ),
                  const Text(MoneyStrings.gstIncluded),
                  const SizedBox(height: 12),
                  Text(inv.customerName),
                  Text('${inv.sellerName}, GSTIN ${inv.sellerGstin}'),
                ],
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              icon: const Icon(Icons.copy_rounded),
              label: const Text(MoneyStrings.invoiceCopy),
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                await Clipboard.setData(ClipboardData(text: asText(inv)));
                messenger.showSnackBar(
                  const SnackBar(content: Text(MoneyStrings.invoiceCopied)),
                );
              },
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              icon: const Icon(Icons.mail_outline_rounded),
              label: const Text(MoneyStrings.invoiceEmail),
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                final uri = Uri(
                  scheme: 'mailto',
                  queryParameters: {
                    'subject': '${MoneyStrings.invoiceTitle} ${inv.number}',
                    'body': asText(inv),
                  },
                );
                var ok = false;
                try {
                  ok = await ref.read(linkOpenerProvider)(uri);
                } catch (_) {}
                if (!ok) {
                  messenger.showSnackBar(
                    const SnackBar(content: Text(MoneyStrings.invoiceNoMail)),
                  );
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}

final _invoiceProvider = FutureProvider.autoDispose.family<InvoiceDto, String>(
  (ref, id) => ref.watch(moneyRepositoryProvider).invoice(id),
);
