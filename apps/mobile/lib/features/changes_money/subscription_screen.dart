import '../../core/features/feature_flags.dart';
import '../../core/features/feature_keys.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../core/network/read_refresh.dart';
import '../../core/ui/theme.dart';
import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import '../customer/calendar/calendar_strings.dart';
import '../customer/calendar/defaults_sheet.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import '../customer/home/vehicle_header.dart';
import 'routes.dart';
import 'strings.dart';

/// My Subscription: the service landing page. It shows what the customer pays
/// for and what they get (SUB-01, SUB-02, SUB-03, SUB-09, SUB-10), with the
/// add-ons they have booked that the crew has not yet completed.
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
    final addons = ref.watch(addonsProvider).value;
    // Booked add-ons the crew has not completed yet, for this vehicle.
    final open = [
      for (final r in addons?.requests ?? const <AddonRequestDto>[])
        if ((r.vehicleId == null || r.vehicleId == widget.vehicleId) &&
            (r.status == 'Requested' || r.status == 'Scheduled'))
          r,
    ];
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
          onRefresh: () => refreshAll(
              ref, () => ref.read(subscriptionProvider(widget.vehicleId).future)),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              VehicleHeader(widget.vehicleId),
              _PlanHero(s),
              const SizedBox(height: 16),
              if (s.canPayNext) ...[
                PrimaryButton(
                    label: MoneyStrings.payNext, busy: _busy, onPressed: _payNext),
                const SizedBox(height: 16),
              ],
              if (s.planInclusions.isNotEmpty) ...[
                const SectionLabel(MoneyStrings.whatYouGet),
                const SizedBox(height: 8),
                SectionCard(
                  child: Column(
                    children: [for (final i in s.planInclusions) _Check(i)],
                  ),
                ),
                const SizedBox(height: 16),
              ],
              const SectionLabel(MoneyStrings.yourSchedule),
              const SizedBox(height: 8),
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(s.vehicle, style: Theme.of(context).textTheme.titleMedium),
                    if (s.registration.isNotEmpty) Text(s.registration),
                    Text(s.society),
                    const SizedBox(height: 8),
                    if (s.cutoffTime != null)
                      Text('${MoneyStrings.cutoff}: ${formatClock(s.cutoffTime!)}'),
                    if (s.interiorDay != null)
                      Text('${MoneyStrings.interiorDay}: ${s.interiorDay}'),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              const SectionLabel(MoneyStrings.planDetails),
              const SizedBox(height: 8),
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${MoneyStrings.expiresOn} ${formatDate(s.endDate)}'),
                    Text('${MoneyStrings.monthly}: ${formatRupees(s.monthlyPriceRupees)}'),
                    Text('${MoneyStrings.paymentMethod}: ${s.paymentMethod}'),
                    if (s.planCode != null) Text('${MoneyStrings.planId}: ${s.planCode}'),
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
              if (open.isNotEmpty) ...[
                const SizedBox(height: 16),
                const SectionLabel(MoneyStrings.yourAddons),
                const SizedBox(height: 8),
                for (final r in open) _AddonTile(r),
              ],
              const SizedBox(height: 20),
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
              if ((s.status == 'Active' || s.status == 'Paused') &&
                  ref.watch(featureOnProvider(FeatureKeys.skipPause)))
                OutlinedButton(
                  onPressed: () => context.push(pausePath(widget.vehicleId)),
                  child: const Text(MoneyStrings.pauseService),
                ),
              if (ref.watch(featureOnProvider(FeatureKeys.billingHistory)))
                OutlinedButton(
                  onPressed: () => context.push(billingPath(widget.vehicleId)),
                  child: const Text(MoneyStrings.billingHistory),
                ),
              if (s.status == 'Active' &&
                  ref.watch(featureOnProvider(FeatureKeys.addons)))
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

/// The big card at the top: the plan, what it costs and when it runs out.
class _PlanHero extends StatelessWidget {
  const _PlanHero(this.s);

  final SubscriptionDto s;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    final progress = s.cycleDays == 0 ? 0.0 : 1 - (s.daysLeft / s.cycleDays);
    final tone = switch (s.status) {
      'Active' => ChipTone.ok,
      'Paused' || 'Activating' => ChipTone.info,
      _ => ChipTone.warn,
    };
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [b.gold.withValues(alpha: 0.30), b.card2],
        ),
        border: Border.all(color: b.gold.withValues(alpha: 0.6)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Symbols.workspace_premium_rounded, color: b.goldHi, size: 28),
              const SizedBox(width: 10),
              Expanded(
                child: Text(s.planName ?? MoneyStrings.noPlanName,
                    style: text.headlineSmall),
              ),
              StatusChip(s.status, tone: tone),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(formatRupees(s.monthlyPriceRupees), style: text.displaySmall),
              const SizedBox(width: 6),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(MoneyStrings.perMonth,
                    style: text.bodyMedium?.copyWith(color: b.mute)),
              ),
              if (s.planListPriceRupees != null &&
                  s.planListPriceRupees! > s.monthlyPriceRupees) ...[
                const SizedBox(width: 10),
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    formatRupees(s.planListPriceRupees!),
                    style: text.bodyMedium?.copyWith(
                        color: b.mute, decoration: TextDecoration.lineThrough),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Semantics(
                label: MoneyStrings.daysLeft(s.daysLeft),
                child: ExcludeSemantics(
                  child: SizedBox(
                    width: 64,
                    height: 64,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        SizedBox(
                          width: 64,
                          height: 64,
                          child: CircularProgressIndicator(
                              value: progress.clamp(0.0, 1.0).toDouble(),
                              strokeWidth: 6),
                        ),
                        Text('${s.daysLeft}', style: text.titleLarge),
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
                    Text(MoneyStrings.daysLeft(s.daysLeft), style: text.titleMedium),
                    Text('${MoneyStrings.expiresOnLong} ${formatDate(s.endDate)}',
                        style: text.bodyMedium?.copyWith(color: b.mute)),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// One thing the plan includes.
class _Check extends StatelessWidget {
  const _Check(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Symbols.check_circle_rounded,
                size: 20, color: context.brand.ok, fill: 1),
            const SizedBox(width: 10),
            Expanded(child: Text(text)),
          ],
        ),
      );
}

/// A booked add-on that the crew has not completed yet.
class _AddonTile extends StatelessWidget {
  const _AddonTile(this.r);

  final AddonRequestDto r;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: SectionCard(
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: b.spa.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Symbols.star_rounded, color: b.spa, fill: 1),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(r.service, style: text.titleMedium),
                  Text(
                    '${formatDate(r.date)} · ${MoneyStrings.addonFinishBy} ${formatClock(r.finishBy)}',
                    style: text.bodySmall?.copyWith(color: b.mute),
                  ),
                  if (r.priceRupees != null)
                    Text(formatRupees(r.priceRupees!),
                        style: text.bodySmall?.copyWith(color: b.mute)),
                ],
              ),
            ),
            StatusChip(r.status, tone: ChipTone.info),
          ],
        ),
      ),
    );
  }
}
