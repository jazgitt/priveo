import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../l10n/app_localizations.dart';
import '../../core/providers.dart';
import '../support/widgets.dart' show linkOpenerProvider;
import '../customer/home/customer_home_data.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import 'routes.dart';
import 'strings.dart';

Future<DateTime?> _pickFutureDate(BuildContext context, DateTime? current) {
  final now = DateTime.now();
  final first = DateTime(
    now.year,
    now.month,
    now.day,
  ).add(const Duration(days: 1));
  return showDatePicker(
    context: context,
    initialDate: current ?? first,
    firstDate: first,
    lastDate: first.add(const Duration(days: 180)),
  );
}

/// Deep Spa as an add-on for a vehicle with an Active subscription (ADD-01 to
/// ADD-05, ADD-10): one preferred date and a finish-by time, then the UPI screen.
class AddonScreen extends ConsumerStatefulWidget {
  const AddonScreen({super.key, required this.vehicleId, this.standalone = false});

  final String vehicleId;
  final bool standalone;

  @override
  ConsumerState<AddonScreen> createState() => _AddonScreenState();
}

class _AddonScreenState extends ConsumerState<AddonScreen> {
  DateTime? _date;
  String _finishBy = '12:00';
  bool _busy = false;
  String? _error;

  Future<void> _confirm(AddonOfferDto offer) async {
    final date = _date;
    if (date == null) {
      setState(() => _error = MoneyStrings.addonPickDate);
      return;
    }
    setState(() => _busy = true);
    try {
      final repo = ref.read(moneyRepositoryProvider);
      final r = widget.standalone
          ? await repo.requestStandalone(vehicleId: widget.vehicleId, date: date,
              finishBy: _finishBy, mobile: '', notes: '')
          : await repo.requestAddon(widget.vehicleId, date, _finishBy);
      ref.invalidate(addonsProvider);
      if (!mounted) return;
      if (r.paymentId != null) {
        await context.push(payPath(r.paymentId!));
        ref.invalidate(addonsProvider);
      }
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel(AddonRequestDto r) async {
    try {
      await ref.read(moneyRepositoryProvider).cancelAddon(r.id);
      ref.invalidate(addonsProvider);
      if (mounted) showMessage(context, MoneyStrings.addonCancelled);
    } catch (e) {
      if (mounted) showFailure(context, e);
    }
  }

  Future<void> _change(AddonRequestDto r) async {
    var day = r.requestedDate ?? r.date;
    var finish = r.requestedFinishBy ?? r.finishBy;
    final l = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, set) => AlertDialog(
          title: Text(l.addonChangeAction),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextButton(
                onPressed: () async {
                  final picked = await _pickFutureDate(context, day);
                  if (picked != null) set(() => day = picked);
                },
                child: Text(formatDate(day)),
              ),
              DropdownButtonFormField<String>(
                initialValue: finish,
                items: [
                  for (final t in halfHourSteps())
                    DropdownMenuItem(value: t, child: Text(formatClock(t))),
                ],
                onChanged: (v) => finish = v ?? finish,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialog, false),
              child: Text(l.addVehicleBack),
            ),
            TextButton(
              onPressed: () => Navigator.pop(dialog, true),
              child: Text(l.continueButton),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;
    try {
      await ref
          .read(dioProvider)
          .patch(
            '/v1/customer/addons/${r.id}',
            data: {
              'date':
                  '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}',
              'finish_by': finish,
            },
          );
      ref.invalidate(addonsProvider);
    } catch (e) {
      if (mounted) showFailure(context, e);
    }
  }

  Future<void> _support() async {
    try {
      final data =
          (await ref
                  .read(dioProvider)
                  .get<Map<String, dynamic>>('/v1/auth/support-contact'))
              .data!;
      await ref.read(linkOpenerProvider)(
        Uri(scheme: 'tel', path: data['helpline'] as String),
      );
    } catch (e) {
      if (mounted) showFailure(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final addons = ref.watch(addonsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(widget.standalone ? MoneyStrings.standaloneTitle : MoneyStrings.addonTitle)),
      body: addons.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(addonsProvider),
        ),
        data: (a) {
          if (a.offers.isEmpty) {
            return Center(
              child: Text(AppLocalizations.of(context).addonNoOffers),
            );
          }
          final offer = a.offers.first;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      offer.name,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    Text(offer.description),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Text(
                          formatRupees(offer.priceRupees),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        if (offer.listPriceRupees != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            formatRupees(offer.listPriceRupees!),
                            style: const TextStyle(
                              decoration: TextDecoration.lineThrough,
                            ),
                          ),
                        ],
                        const Spacer(),
                        Text(MoneyStrings.addonDuration(offer.durationMinutes)),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed: () async {
                  final d = await _pickFutureDate(context, _date);
                  if (d != null) {
                    setState(() {
                      _date = d;
                      _error = null;
                    });
                  }
                },
                child: Text(
                  '${MoneyStrings.addonDate}: '
                  '${_date == null ? '--' : formatDate(_date!)}',
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _finishBy,
                decoration: const InputDecoration(
                  labelText: MoneyStrings.addonFinishBy,
                ),
                items: [
                  for (final t in halfHourSteps())
                    DropdownMenuItem(value: t, child: Text(formatClock(t))),
                ],
                onChanged: (v) => setState(() => _finishBy = v ?? _finishBy),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              if (_date != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    MoneyStrings.addonSummary(
                      formatDate(_date!),
                      formatClock(_finishBy),
                      formatRupees(offer.priceRupees),
                    ),
                  ),
                ),
              const SizedBox(height: 16),
              PrimaryButton(
                label: MoneyStrings.addonConfirm,
                busy: _busy,
                onPressed: () => _confirm(offer),
              ),
              const SizedBox(height: 24),
              const SectionLabel(MoneyStrings.addonRequests),
              const SizedBox(height: 8),
              if (a.requests.isEmpty) const Text(MoneyStrings.addonNone),
              for (final r in a.requests.where(
                (r) => r.vehicleId == null || r.vehicleId == widget.vehicleId,
              ))
                _RequestTile(
                  r,
                  onCancel: () => _cancel(r),
                  onChange: () => _change(r),
                  onSupport: _support,
                ),
              const SizedBox(height: 16),
              if (!widget.standalone) TextButton(
                onPressed: () => context.push(standalonePath()),
                child: const Text(MoneyStrings.standaloneLink),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _RequestTile extends StatelessWidget {
  const _RequestTile(
    this.r, {
    required this.onCancel,
    required this.onChange,
    required this.onSupport,
  });

  final AddonRequestDto r;
  final VoidCallback onCancel;
  final VoidCallback onChange, onSupport;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: SectionCard(
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${r.service}, ${formatDate(r.date)}',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                Text('Finish by ${formatClock(r.finishBy)}'),
                if (r.paymentStatus != null)
                  Text('Payment: ${r.paymentStatus}'),
                if (r.changeRequested)
                  Text(AppLocalizations.of(context).addonChangeRequest),
                if (r.crewName != null)
                  Text('${r.crewName} · ${r.startTime ?? ''}'),
                if (r.visitId != null)
                  TextButton(
                    onPressed: () =>
                        context.push('/customer/visits/${r.visitId}'),
                    child: Text(AppLocalizations.of(context).addonViewProof),
                  ),
                if (!r.canChange &&
                    (r.status == 'Requested' || r.status == 'Scheduled'))
                  TextButton(
                    onPressed: onSupport,
                    child: Text(
                      AppLocalizations.of(context).addonSupportClosed,
                    ),
                  ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              StatusChip(
                r.status,
                tone: r.status == 'Completed'
                    ? ChipTone.ok
                    : r.status == 'Scheduled'
                    ? ChipTone.info
                    : ChipTone.neutral,
              ),
              if (r.canChange)
                TextButton(
                  onPressed: onChange,
                  child: Text(AppLocalizations.of(context).addonChangeAction),
                ),
              if (r.canChange)
                TextButton(
                  onPressed: onCancel,
                  child: const Text(MoneyStrings.addonCancel),
                ),
            ],
          ),
        ],
      ),
    ),
  );
}

/// Standalone Spa shares the booking/payment/history UI without a plan.
class StandaloneDeepSpaScreen extends ConsumerWidget {
  const StandaloneDeepSpaScreen({super.key, this.vehicleId});
  final String? vehicleId;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (vehicleId != null) return AddonScreen(vehicleId: vehicleId!, standalone: true);
    final home = ref.watch(customerHomeProvider);
    return Scaffold(
      appBar: AppBar(title: const Text(MoneyStrings.standaloneTitle)),
      body: home.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, _) => ErrorView(onRetry: () => ref.invalidate(customerHomeProvider)),
        data: (h) => ListView(children: [
          const ListTile(title: Text('Choose your vehicle'),
            subtitle: Text('Priveo adds standalone vehicles without a subscription.')),
          for (final v in h.vehicles)
            if (v.subscriptionStatus == null)
              ListTile(title: Text(v.registration), subtitle: Text(v.model),
                onTap: () => context.push(standalonePath(v.id))),
          if (!h.vehicles.any((v) => v.subscriptionStatus == null))
            const ListTile(title: Text('Contact Priveo to add a standalone vehicle.')),
        ]),
      ),
    );
  }
}
