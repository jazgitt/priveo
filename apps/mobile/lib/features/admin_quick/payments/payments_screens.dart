import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../changes_money/money_widgets.dart';
import '../../changes_money/strings.dart';
import 'admin_payments_data.dart';

/// Payments the customers have marked as paid, for the admin to confirm or
/// send back (ADM-ACC-07 b, ADM-PAY-02, ADM-PAY-03, ADM-PAY-07).
class PaymentsToConfirmScreen extends ConsumerStatefulWidget {
  const PaymentsToConfirmScreen({super.key});

  @override
  ConsumerState<PaymentsToConfirmScreen> createState() => _PaymentsState();
}

class _PaymentsState extends ConsumerState<PaymentsToConfirmScreen> {
  String? _busyId;

  Future<void> _act(AdminPaymentDto p, bool confirm) async {
    setState(() => _busyId = p.id);
    final repo = ref.read(adminPaymentsRepositoryProvider);
    try {
      if (confirm) {
        await repo.confirm(p.id);
      } else {
        await repo.reject(p.id);
      }
      ref.invalidate(paymentsToConfirmProvider);
      if (mounted) {
        showMessage(context,
            confirm ? MoneyStrings.adminConfirmed : MoneyStrings.adminRejected);
      }
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final payments = ref.watch(paymentsToConfirmProvider);
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.adminPaymentsTitle)),
      body: payments.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(e),
            onRetry: () => ref.invalidate(paymentsToConfirmProvider)),
        data: (rows) => RefreshIndicator(
          onRefresh: () => ref.refresh(paymentsToConfirmProvider.future),
          child: rows.isEmpty
              ? ListView(children: const [
                  Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(MoneyStrings.adminNoPayments)),
                ])
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: rows.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 12),
                  itemBuilder: (context, i) {
                    final p = rows[i];
                    final busy = _busyId == p.id;
                    return SectionCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                    '${p.customerName}${p.flat.isEmpty ? '' : ', ${p.flat}'}',
                                    style: Theme.of(context).textTheme.titleSmall),
                              ),
                              Text(formatRupees(p.amountRupees),
                                  style: Theme.of(context).textTheme.titleMedium),
                            ],
                          ),
                          Text('${p.kind}: ${p.description}'),
                          if (p.vehicle.isNotEmpty) Text(p.vehicle),
                          Text(MoneyStrings.statusDue(formatDate(p.dueDate))),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton(
                                  onPressed: busy ? null : () => _act(p, false),
                                  child: const Text(MoneyStrings.adminReject),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: FilledButton(
                                  onPressed: busy ? null : () => _act(p, true),
                                  child: const Text(MoneyStrings.adminConfirm),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}

/// Alerts the money rules raise: a payment marked paid, a subscription made
/// Inactive after 7 days over due (ADM-PAY-11, ADM-SUB-03).
class AdminAlertsScreen extends ConsumerWidget {
  const AdminAlertsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alerts = ref.watch(adminAlertsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.adminAlertsTitle)),
      body: alerts.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(e),
            onRetry: () => ref.invalidate(adminAlertsProvider)),
        data: (rows) => rows.isEmpty
            ? const Center(child: Text(MoneyStrings.adminNoAlerts))
            : ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: rows.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (context, i) {
                  final a = rows[i];
                  return SectionCard(
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(a.message,
                                  style: a.read
                                      ? null
                                      : const TextStyle(fontWeight: FontWeight.w700)),
                              Text(formatDate(a.createdAt.toLocal())),
                            ],
                          ),
                        ),
                        if (!a.read)
                          TextButton(
                            onPressed: () async {
                              try {
                                await ref
                                    .read(adminPaymentsRepositoryProvider)
                                    .markRead(a.id);
                                ref.invalidate(adminAlertsProvider);
                              } catch (e) {
                                if (context.mounted) showFailure(context, e);
                              }
                            },
                            child: const Text(MoneyStrings.adminMarkRead),
                          ),
                      ],
                    ),
                  );
                },
              ),
      ),
    );
  }
}
