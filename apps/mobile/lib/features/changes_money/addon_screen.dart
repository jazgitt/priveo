import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';
import '../../l10n/app_localizations.dart';
import '../../core/providers.dart';
import '../support/widgets.dart' show linkOpenerProvider;
import '../customer/home/customer_home_data.dart';

import '../../core/ui/theme.dart';
import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/money_models.dart';
import 'data/money_repository.dart';
import 'money_widgets.dart';
import '../customer/home/vehicle_header.dart';
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

  /// The add-on the customer opened, by catalogue ID, when there is more than one.
  String? _chosen;

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
              finishBy: _finishBy, mobile: '', notes: '',
              addon: offer.code, service: offer.service)
          : await repo.requestAddon(widget.vehicleId, date, _finishBy,
              addon: offer.code, service: offer.service);
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
      appBar: AppBar(title: const Text(MoneyStrings.addonTitle)),
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
          // Several add-ons: the customer first chooses one. With one, it opens at once.
          final many = a.offers.length > 1;
          final picked = a.offers.where((o) => o.code == _chosen).firstOrNull;
          if (many && picked == null) {
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                VehicleHeader(widget.vehicleId),
                const SectionLabel(MoneyStrings.addonChoose),
                const SizedBox(height: 8),
                for (final o in a.offers)
                  _OfferCard(o, onTap: () => setState(() {
                        _chosen = o.code;
                        _error = null;
                      })),
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
              ],
            );
          }
          final offer = picked ?? a.offers.first;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              VehicleHeader(widget.vehicleId),
              if (many)
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => setState(() => _chosen = null),
                    icon: const Icon(Symbols.arrow_back_rounded),
                    label: const Text(MoneyStrings.addonChooseAnother),
                  ),
                ),
              _SpaHero(offer),
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
            ],
          );
        },
      ),
    );
  }
}

/// One add-on in the list the customer chooses from: its name, a line about it,
/// and its price.
class _OfferCard extends StatelessWidget {
  const _OfferCard(this.offer, {required this.onTap});

  final AddonOfferDto offer;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    final pitch = offer.description
        .split('\n')
        .map((l) => l.trim())
        .firstWhere((l) => l.isNotEmpty, orElse: () => '');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Semantics(
        button: true,
        label: '${offer.name}, ${formatRupees(offer.priceRupees)}',
        child: ExcludeSemantics(
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(18),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                color: b.card2,
                border: Border.all(color: b.spa.withValues(alpha: 0.5)),
              ),
              child: Row(children: [
                Icon(Symbols.star_rounded, color: b.spa, size: 28, fill: 1),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(offer.name, style: text.titleMedium),
                    if (pitch.isNotEmpty)
                      Text(pitch, style: text.bodyMedium?.copyWith(color: b.mute),
                          maxLines: 2, overflow: TextOverflow.ellipsis),
                    Text(MoneyStrings.addonDuration(offer.durationMinutes),
                        style: text.bodySmall?.copyWith(color: b.mute)),
                  ]),
                ),
                const SizedBox(width: 12),
                Text(formatRupees(offer.priceRupees), style: text.titleMedium),
              ]),
            ),
          ),
        ),
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
                  '${r.title}, ${formatDate(r.date)}',
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
      appBar: AppBar(title: const Text(MoneyStrings.addonTitle)),
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

/// The Deep Spa landing card: what the service is, what it includes and what
/// it costs. The first paragraph of the catalogue description is the pitch;
/// every further line is shown as something that is included.
class _SpaHero extends StatelessWidget {
  const _SpaHero(this.offer);

  final AddonOfferDto offer;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    final lines = [
      for (final l in offer.description.split('\n'))
        if (l.trim().isNotEmpty) l.trim(),
    ];
    final pitch = lines.isEmpty ? '' : lines.first;
    final included = lines.length > 1 ? lines.sublist(1) : const <String>[];
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [b.spa.withValues(alpha: 0.38), b.card2],
        ),
        border: Border.all(color: b.spa.withValues(alpha: 0.7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Symbols.star_rounded, color: b.spa, size: 34, fill: 1),
              const SizedBox(width: 10),
              Expanded(child: Text(offer.name, style: text.headlineMedium)),
            ],
          ),
          if (pitch.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(pitch, style: text.bodyLarge),
          ],
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.end,
            children: [
              Text(formatRupees(offer.priceRupees), style: text.displaySmall),
              if (offer.listPriceRupees != null &&
                  offer.listPriceRupees! > offer.priceRupees)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    formatRupees(offer.listPriceRupees!),
                    style: text.bodyMedium?.copyWith(
                        color: b.mute, decoration: TextDecoration.lineThrough),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Symbols.schedule_rounded, size: 18, color: b.mute),
                    const SizedBox(width: 4),
                    Text(MoneyStrings.addonDuration(offer.durationMinutes),
                        style: text.bodyMedium?.copyWith(color: b.mute)),
                  ],
                ),
              ),
            ],
          ),
          if (included.isNotEmpty) ...[
            const SizedBox(height: 18),
            Text(MoneyStrings.whatsIncluded, style: text.titleMedium),
            const SizedBox(height: 8),
            for (final i in included)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Symbols.check_circle_rounded,
                        size: 20, color: b.ok, fill: 1),
                    const SizedBox(width: 10),
                    Expanded(child: Text(i)),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}
