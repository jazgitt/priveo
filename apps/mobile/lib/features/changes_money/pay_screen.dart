import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import 'strings.dart';

/// The UPI payment screen (PAY-05, PAY-06, PAY-07, SUB-09, ADD-05): the QR
/// code, the UPI ID, and "I've paid", which moves the payment to Initiated.
class PayScreen extends ConsumerStatefulWidget {
  const PayScreen({super.key, required this.paymentId});

  final String paymentId;

  @override
  ConsumerState<PayScreen> createState() => _PayScreenState();
}

class _PayScreenState extends ConsumerState<PayScreen> {
  bool _busy = false;
  PaymentDetailDto? _submitted;

  Future<void> _paid() async {
    setState(() => _busy = true);
    try {
      final d = await ref.read(moneyRepositoryProvider).markPaid(widget.paymentId);
      if (mounted) setState(() => _submitted = d);
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final submitted = _submitted;
    if (submitted != null) return _Submitted(submitted);
    final detail = ref.watch(paymentDetailProvider(widget.paymentId));
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.payTitle)),
      body: detail.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(e),
            onRetry: () => ref.invalidate(paymentDetailProvider(widget.paymentId))),
        data: (d) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(d.payment.description,
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: Text('${MoneyStrings.payAmount}: '
                      '${formatRupees(d.instructions.amountRupees)}'),
                ),
                const SizedBox(width: 8),
                PaymentStatusChip(d.payment),
              ],
            ),
            const SizedBox(height: 16),
            _QrBox(uri: d.instructions.upiUri),
            const SizedBox(height: 12),
            const Text(MoneyStrings.payHow),
            const SizedBox(height: 12),
            SectionCard(
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SectionLabel(MoneyStrings.upiId),
                        const SizedBox(height: 4),
                        SelectableText(d.instructions.upiId,
                            style: Theme.of(context).textTheme.titleMedium),
                        Text(d.instructions.payeeName),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: MoneyStrings.copy,
                    icon: const Icon(Icons.copy),
                    onPressed: () async {
                      await Clipboard.setData(
                          ClipboardData(text: d.instructions.upiId));
                      if (context.mounted) showMessage(context, MoneyStrings.copied);
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            if (d.payment.status == 'Due' || d.payment.status == 'Over due')
              PrimaryButton(
                  label: MoneyStrings.ivePaid, busy: _busy, onPressed: _paid),
          ],
        ),
      ),
    );
  }
}

class _QrBox extends StatelessWidget {
  const _QrBox({required this.uri});

  final String uri;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Center(
      child: Container(
        width: 220,
        height: 220,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: scheme.outlineVariant),
        ),
        child: uri.isEmpty
            ? const Padding(
                padding: EdgeInsets.all(16),
                child: Text(MoneyStrings.qrMissing,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.black87)),
              )
            : Semantics(label: 'UPI QR code for the payable amount',
                child: QrImageView(data: uri, size: 220, backgroundColor: Colors.white)),
      ),
    );
  }
}

/// PAY-07: the payment is submitted and waits for Priveo to confirm it.
class _Submitted extends StatelessWidget {
  const _Submitted(this.detail);

  final PaymentDetailDto detail;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
            title: const Text(MoneyStrings.submittedTitle),
            automaticallyImplyLeading: false),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.hourglass_top_rounded, size: 56),
              const SizedBox(height: 16),
              Text(MoneyStrings.submittedTitle,
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(detail.payment.description, textAlign: TextAlign.center),
              if (detail.vehicle.isNotEmpty) Text(detail.vehicle, textAlign: TextAlign.center),
              if (detail.serviceDetails['cutoff_time'] != null)
                Text('Service cutoff: ${formatClock(detail.serviceDetails['cutoff_time'] as String)}'),
              if (detail.serviceDetails['interior_day'] != null)
                Text('Interior care day: ${detail.serviceDetails['interior_day']}'),
              const SizedBox(height: 8),
              Text(
                  MoneyStrings.submittedBody(
                      formatRupees(detail.instructions.amountRupees)),
                  textAlign: TextAlign.center),
              const SizedBox(height: 8),
              PaymentStatusChip(detail.payment),
              const SizedBox(height: 32),
              PrimaryButton(
                  label: MoneyStrings.goHome, onPressed: () => context.go('/customer')),
            ],
          ),
        ),
      );
}
