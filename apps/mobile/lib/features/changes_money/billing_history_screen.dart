import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/read_refresh.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'invoice_screen.dart';
import 'money_widgets.dart';
import 'strings.dart';
import 'routes.dart';

/// The subscription's payments, newest first (SUB-06), with an invoice where
/// the admin made one (SUB-12). A payment still to be paid opens the UPI screen.
class BillingHistoryScreen extends ConsumerWidget {
  const BillingHistoryScreen({super.key, required this.vehicleId});

  final String vehicleId;

  // SUB-12: the invoice opens as a page with an authenticated PDF preview.
  void _showInvoice(BuildContext context, PaymentDto p) =>
      Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => InvoiceScreen(paymentId: p.id)),
      );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(billingHistoryProvider(vehicleId));
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.historyTitle)),
      body: history.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(billingHistoryProvider(vehicleId)),
        ),
        data: (rows) => rows.isEmpty
            ? const Center(child: Text(MoneyStrings.historyEmpty))
            : RefreshIndicator(
          onRefresh: () => refreshAll(ref, () => ref.read(billingHistoryProvider(vehicleId).future)),
          child: ListView.separated(
          physics: const AlwaysScrollableScrollPhysics(),
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
                                Text(
                                  p.description,
                                  style: Theme.of(context).textTheme.titleSmall,
                                ),
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
                                  onPressed: () => _showInvoice(context, p),
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
      ),
    );
  }
}
