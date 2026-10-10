import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import 'strings.dart';
import 'routes.dart';

/// The subscription's payments, newest first (SUB-06), with an invoice where
/// the admin made one (SUB-12). A payment still to be paid opens the UPI screen.
class BillingHistoryScreen extends ConsumerWidget {
  const BillingHistoryScreen({super.key, required this.vehicleId});

  final String vehicleId;

  Future<void> _showInvoice(BuildContext context, WidgetRef ref, PaymentDto p) async {
    try {
      final inv = await ref.read(moneyRepositoryProvider).invoice(p.id);
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text(MoneyStrings.invoiceTitle),
          content: _InvoiceBody(inv),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(c), child: const Text('Close')),
          ],
        ),
      );
    } catch (e) {
      if (context.mounted) showFailure(context, e);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(billingHistoryProvider(vehicleId));
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.historyTitle)),
      body: history.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(e),
            onRetry: () => ref.invalidate(billingHistoryProvider(vehicleId))),
        data: (rows) => rows.isEmpty
            ? const Center(child: Text(MoneyStrings.historyEmpty))
            : ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: rows.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (context, i) {
                  final p = rows[i];
                  final unpaid = p.status == 'Due' || p.status == 'Over due';
                  return SectionCard(
                    child: InkWell(
                      onTap: unpaid ? () => context.push(payPath(p.id)) : null,
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(p.description,
                                    style: Theme.of(context).textTheme.titleSmall),
                                Text(formatRupees(p.amountRupees)),
                                Text(formatDate(p.dueDate)),
                              ],
                            ),
                          ),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              PaymentStatusChip(p),
                              if (p.invoiceNumber != null)
                                TextButton(
                                  onPressed: () => _showInvoice(context, ref, p),
                                  child: const Text(MoneyStrings.invoice),
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}

class _InvoiceBody extends StatelessWidget {
  const _InvoiceBody(this.inv);

  final InvoiceDto inv;

  @override
  Widget build(BuildContext context) => Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(inv.number, style: Theme.of(context).textTheme.titleMedium),
          Text(formatDate(inv.issuedOn)),
          const SizedBox(height: 8),
          Text(inv.description),
          Text(formatRupees(inv.amountRupees)),
          const Text(MoneyStrings.gstIncluded),
          const SizedBox(height: 8),
          Text(inv.customerName),
          Text('${inv.sellerName}, GSTIN ${inv.sellerGstin}'),
        ],
      );
}
