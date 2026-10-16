import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/read_refresh.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import '../customer/calendar/calendar_strings.dart';
import '../customer/calendar/defaults_sheet.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import 'strings.dart';
import 'routes.dart';

/// My Subscription (SUB-01, SUB-02, SUB-03, SUB-09, SUB-10).
class SubscriptionScreen extends ConsumerStatefulWidget {
  const SubscriptionScreen({super.key, required this.vehicleId});

  final String vehicleId;

  @override
  ConsumerState<SubscriptionScreen> createState() => _SubscriptionScreenState();
}

class _SubscriptionScreenState extends ConsumerState<SubscriptionScreen> {
  bool _busy = false;

  Future<void> _payNext() async {
    setState(() => _busy = true);
    try {
      final d = await ref.read(moneyRepositoryProvider).payNext(widget.vehicleId);
      if (!mounted) return;
      await context.push(payPath(d.payment.id));
      ref.invalidate(subscriptionProvider(widget.vehicleId));
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sub = ref.watch(subscriptionProvider(widget.vehicleId));
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.subTitle)),
      body: sub.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(e),
            onRetry: () => ref.invalidate(subscriptionProvider(widget.vehicleId))),
        data: (s) => RefreshIndicator(
          onRefresh: () => refreshAll(ref, () => ref.read(subscriptionProvider(widget.vehicleId).future)),
          child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            _PlanCard(s),
            const SizedBox(height: 12),
            SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(s.vehicle, style: Theme.of(context).textTheme.titleMedium),
                  if (s.registration.isNotEmpty) Text(s.registration),
                  Text(s.society),
                  if (s.cutoffTime != null)
                    Text('${MoneyStrings.cutoff}: ${formatClock(s.cutoffTime!)}'),
                  if (s.interiorDay != null)
                    Text('${MoneyStrings.interiorDay}: ${s.interiorDay}'),
                ],
              ),
            ),
            if (s.latestPayment != null) ...[
              const SizedBox(height: 12),
              SectionCard(
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SectionLabel(MoneyStrings.latestPayment),
                          const SizedBox(height: 4),
                          Text(formatRupees(s.latestPayment!.amountRupees)),
                        ],
                      ),
                    ),
                    PaymentStatusChip(s.latestPayment!),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 20),
            if (s.canPayNext)
              PrimaryButton(
                  label: MoneyStrings.payNext, busy: _busy, onPressed: _payNext),
            const SizedBox(height: 12),
            if (s.status == 'Active')
              OutlinedButton(
                onPressed: () async {
                  final saved = await showDefaultsSheet(
                    context,
                    vehicleId: widget.vehicleId,
                    cutoff: s.cutoffTime,
                    interiorDay: s.interiorDay,
                  );
                  if (saved) ref.invalidate(subscriptionProvider(widget.vehicleId));
                },
                child: const Text(CalStrings.editDefaults),
              ),
            if (s.status == 'Active' || s.status == 'Paused')
              OutlinedButton(
                onPressed: () => context.push(pausePath(widget.vehicleId)),
                child: const Text(MoneyStrings.pauseService),
              ),
            OutlinedButton(
              onPressed: () => context.push(billingPath(widget.vehicleId)),
              child: const Text(MoneyStrings.billingHistory),
            ),
            if (s.status == 'Active')
              OutlinedButton(
                onPressed: () => context.push(addonsPath(widget.vehicleId)),
                child: const Text(MoneyStrings.addons),
              ),
          ],
        ),
        ),
      ),
    );
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard(this.s);

  final SubscriptionDto s;

  @override
  Widget build(BuildContext context) {
    final progress = s.cycleDays == 0 ? 0.0 : 1 - (s.daysLeft / s.cycleDays);
    final tone = switch (s.status) {
      'Active' => ChipTone.ok,
      'Paused' || 'Activating' => ChipTone.info,
      _ => ChipTone.warn,
    };
    return SectionCard(
      child: Row(
        children: [
          Semantics(
            label: MoneyStrings.daysLeft(s.daysLeft),
            child: ExcludeSemantics(
              child: SizedBox(
                width: 76,
                height: 76,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 76,
                      height: 76,
                      child: CircularProgressIndicator(
                          value: progress.clamp(0.0, 1.0).toDouble(), strokeWidth: 6),
                    ),
                    Text('${s.daysLeft}',
                        style: Theme.of(context).textTheme.titleLarge),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(s.planName ?? MoneyStrings.noPlanName,
                          style: Theme.of(context).textTheme.titleMedium),
                    ),
                    const SizedBox(width: 8),
                    StatusChip(s.status, tone: tone),
                  ],
                ),
                const SizedBox(height: 4),
                Text(MoneyStrings.daysLeft(s.daysLeft)),
                Text('${MoneyStrings.cycle}: ${formatDate(s.cycleStart)} to '
                    '${formatDate(s.renewalDate.subtract(const Duration(days: 1)))}'),
                Text('${MoneyStrings.monthly}: ${formatRupees(s.monthlyPriceRupees)}'),
                Text('${MoneyStrings.paymentMethod}: ${s.paymentMethod}'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
