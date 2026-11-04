import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/read_refresh.dart';

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

  /// The status filter; Initiated is the queue to approve (ADM-PAY-07).
  String? _status = 'Initiated';

  Future<void> _act(AdminPaymentDto p, bool confirm) async {
    setState(() => _busyId = p.id);
    final repo = ref.read(adminPaymentsRepositoryProvider);
    try {
      if (confirm) {
        await repo.confirm(p.id);
      } else {
        await repo.reject(p.id);
      }
      ref.invalidate(adminPaymentsProvider);
      if (mounted) {
        showMessage(
          context,
          confirm ? MoneyStrings.adminApproved : MoneyStrings.adminRejected,
        );
      }
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final payments = ref.watch(adminPaymentsProvider(_status));
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.adminPaymentsTitle)),
      body: Column(
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Row(
              children: [
                for (final st in [null, ...adminPaymentStatuses])
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(
                        st == null
                            ? MoneyStrings.adminAll
                            : paymentStatusText(st),
                      ),
                      selected: _status == st,
                      onSelected: (_) => setState(() => _status = st),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: payments.when(
              skipLoadingOnReload: true,
              skipError: true,
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => ErrorView(
                message: failureText(e),
                onRetry: () => ref.invalidate(adminPaymentsProvider),
              ),
              data: (rows) => RefreshIndicator(
                onRefresh: () => refreshAll(
                  ref,
                  () => ref.read(adminPaymentsProvider(_status).future),
                ),
                child: rows.isEmpty
                    ? ListView(
                        children: const [
                          Padding(
                            padding: EdgeInsets.all(24),
                            child: Text(MoneyStrings.adminNoPayments),
                          ),
                        ],
                      )
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
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleSmall,
                                      ),
                                    ),
                                    Text(
                                      formatRupees(p.amountRupees),
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium,
                                    ),
                                  ],
                                ),
                                Text('${p.kind}: ${p.description}'),
                                if (p.vehicle.isNotEmpty) Text(p.vehicle),
                                Row(
                                  children: [
                                    StatusChip(
                                      paymentStatusText(p.status),
                                      tone: paymentTone(p.status),
                                    ),
                                    const SizedBox(width: 8),
                                    Text(formatDate(p.dueDate)),
                                  ],
                                ),
                                PaymentStatusNote(
                                  message: p.statusMessage,
                                  lastPaymentFailed: p.lastPaymentFailed,
                                ),
                                // Approve and Reject apply to an Initiated payment.
                                if (p.status == 'Initiated') ...[
                                  const SizedBox(height: 8),
                                  Row(
                                    children: [
                                      Expanded(
                                        child: OutlinedButton(
                                          onPressed: busy
                                              ? null
                                              : () => _act(p, false),
                                          child: const Text(
                                            MoneyStrings.adminReject,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: FilledButton(
                                          onPressed: busy
                                              ? null
                                              : () => _act(p, true),
                                          child: const Text(
                                            MoneyStrings.adminApprove,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ],
                            ),
                          );
                        },
                      ),
              ),
            ),
          ),
        ],
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
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(adminAlertsProvider),
        ),
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
                              Text(
                                a.message,
                                style: a.read
                                    ? null
                                    : const TextStyle(
                                        fontWeight: FontWeight.w700,
                                      ),
                              ),
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
