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
import 'invoice_pdf_screen.dart';
import '../../l10n/app_localizations.dart';

/// The invoice for one payment (SUB-12): a formatted page the customer can
/// open as a PDF. Existing text actions remain until step 5.2 adds PDF save/share.
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
                  if (inv.taxDetails case final tax?) ...[
                    if (tax['mock_configuration'] == true) const Text('Mock GST configuration'),
                    Text('Taxable value: ₹${((tax['taxable_paise'] as num) / 100).toStringAsFixed(2)}'),
                    for (final entry in {'cgst_paise': 'CGST', 'sgst_paise': 'SGST', 'igst_paise': 'IGST'}.entries)
                      if ((tax[entry.key] as num) > 0)
                        Text('${entry.value}: ₹${((tax[entry.key] as num) / 100).toStringAsFixed(2)}'),
                  ],
                  const SizedBox(height: 12),
                  Text(inv.customerName),
                  Text('${inv.sellerName}, GSTIN ${inv.sellerGstin}'),
                ],
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              icon: const Icon(Icons.picture_as_pdf),
              label: Text(AppLocalizations.of(context).invoiceOpenPdf),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => InvoicePdfScreen(paymentId: paymentId, number: inv.number))),
            ),
            const SizedBox(height: 8),
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
