import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/api/api.g.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import '../account/account_data.dart' show vehiclePhotoDoneProvider;
import '../account/account_strings.dart';
import '../account/photo_widgets.dart' show VehiclePhotoField;
import '../home/customer_home_data.dart';
import '../../changes_money/routes.dart' show payPath;

final onboardingProvider = FutureProvider.autoDispose<Onboarding>(
  (ref) => ref.watch(apiProvider).onboarding(),
);

final onboardingSummaryProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final r = await ref
          .watch(dioProvider)
          .get<Map<String, dynamic>>('/v1/customer/onboarding-summary');
      return (r.data!['vehicles'] as List).cast<Map<String, dynamic>>();
    });

const _basements = ['B1', 'B2', 'B3', 'B4']; // ONB-13
const _weekdays = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];
final _name = RegExp(r"^[A-Za-z][A-Za-z .'-]{0,79}$"); // ONB-02

/// Every time of day in 30-minute steps (ONB-16), as the API's `HH:MM`.
final cutoffTimes = [
  for (var h = 0; h < 24; h++)
    for (final m in const ['00', '30']) '${h.toString().padLeft(2, '0')}:$m',
];

/// The review a customer goes through at first sign-in (ONB-25): the details
/// the admin entered, one step at a time. The customer fills what is empty,
/// changes what they may change (ONB-26) and confirms. Home opens after that.
class OnboardingReviewScreen extends ConsumerWidget {
  const OnboardingReviewScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final details = ref.watch(onboardingProvider);
    return Scaffold(
      body: SafeArea(
        child: details.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ErrorView(
            message: e is ApiFailure ? e.message : null,
            onRetry: () => ref.invalidate(onboardingProvider),
          ),
          data: (d) => _Review(d),
        ),
      ),
    );
  }
}

/// What the customer has entered for one vehicle.
class _VehicleDraft {
  _VehicleDraft(this.vehicle)
    : basement = _basements.contains(vehicle.parkingBasement)
          ? vehicle.parkingBasement
          : null,
      number = TextEditingController(text: vehicle.parkingNumber),
      cutoff = vehicle.cutoffTime,
      day = vehicle.interiorDay;

  final OnboardingVehicle vehicle;
  String? basement;
  final TextEditingController number;
  String? cutoff;
  String? day;
}

class _Review extends ConsumerStatefulWidget {
  const _Review(this.details);

  final Onboarding details;

  @override
  ConsumerState<_Review> createState() => _ReviewState();
}

class _ReviewState extends ConsumerState<_Review> {
  late final _first = TextEditingController(text: widget.details.firstName);
  late final _last = TextEditingController(text: widget.details.lastName);
  late final _mobile = TextEditingController(text: widget.details.mobile);
  late final _drafts = [
    for (final v in widget.details.vehicles) _VehicleDraft(v),
  ];
  final _scroll = ScrollController();
  int _step = 0;
  bool _busy = false;
  Map<String, String> _errors = {};
  String? _failure;

  // Your details, your society, one step for each vehicle, then the review.
  int get _steps => 3 + _drafts.length;
  bool get _onReview => _step == _steps - 1;

  @override
  void dispose() {
    for (final c in [_first, _last, _mobile, _scroll]) {
      c.dispose();
    }
    for (final d in _drafts) {
      d.number.dispose();
    }
    super.dispose();
  }

  /// The problems on one step, by field. Empty when the step is complete.
  Map<String, String> _check(int step) {
    final l = AppLocalizations.of(context);
    final errors = <String, String>{};
    if (step == 0) {
      if (!_name.hasMatch(_first.text.trim())) {
        errors['first'] = l.enterFirstName;
      }
      if (!_name.hasMatch(_last.text.trim())) {
        errors['last'] = l.enterLastName;
      }
      final mobile = _mobile.text.trim();
      // The number on file stands as it is. A new one must be 10 digits.
      if (mobile != widget.details.mobile &&
          !RegExp(r'^\d{10}$').hasMatch(mobile)) {
        errors['mobile'] = l.enterMobile;
      }
    } else if (step >= 2 && step < _steps - 1) {
      final d = _drafts[step - 2];
      // ONB-22: the vehicle photo is required.
      if (!ref.read(vehiclePhotoDoneProvider(d.vehicle.id))) {
        errors['photo'] = AccountStrings.photoRequired;
      }
      if (d.basement == null) errors['basement'] = l.selectBasement;
      if (!RegExp(r'^\d{1,5}$').hasMatch(d.number.text.trim())) {
        errors['number'] = l.enterParkingNumber;
      }
      if (d.vehicle.hasSubscription) {
        if (d.cutoff == null) errors['cutoff'] = l.selectCutoff;
        if (d.vehicle.asksInteriorDay && d.day == null) {
          errors['day'] = l.selectInteriorDay;
        }
      }
    }
    return errors;
  }

  void _show(int step) {
    setState(() {
      _step = step;
      _errors = {};
      _failure = null;
    });
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  void _continue() {
    FocusScope.of(context).unfocus();
    final errors = _check(_step);
    if (errors.isNotEmpty) {
      setState(() => _errors = errors);
      return;
    }
    _show(_step + 1);
  }

  Future<void> _confirm() async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      await ref
          .read(apiProvider)
          .confirmOnboarding(
            OnboardingAnswers(
              firstName: _first.text.trim(),
              lastName: _last.text.trim(),
              mobile: _mobile.text.trim(),
              vehicles: [
                for (final d in _drafts)
                  VehicleAnswer(
                    id: d.vehicle.id,
                    parkingBasement: d.basement ?? '',
                    parkingNumber: d.number.text.trim(),
                    cutoffTime: d.cutoff,
                    interiorDay: d.day,
                  ),
              ],
            ),
          );
      // Home reads the details again and opens.
      ref.invalidate(customerHomeProvider);
      final summary = ref.read(onboardingSummaryProvider).value ?? [];
      final due = [
        for (final v in summary)
          for (final p in v['payments'] as List)
            if (p['status'] == 'Due' || p['status'] == 'Over due') p,
      ];
      if (due.isNotEmpty && mounted) {
        final router = GoRouter.of(context);
        router.go('/customer');
        router.push(payPath(due.first['id'] as String));
      }
    } on ApiFailure catch (e) {
      if (mounted) setState(() => _failure = e.message ?? l.networkError);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickCutoff(_VehicleDraft d) async {
    // The list opens at the chosen time, or in the early morning.
    const rowHeight = 56.0;
    final start = cutoffTimes.indexOf(d.cutoff ?? '06:00');
    final picked = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: ListView(
          controller: ScrollController(initialScrollOffset: start * rowHeight),
          itemExtent: rowHeight,
          children: [
            for (final t in cutoffTimes)
              ListTile(
                title: Text(formatClock(t)),
                selected: t == d.cutoff,
                trailing: t == d.cutoff
                    ? const Icon(Symbols.check_rounded)
                    : null,
                onTap: () => Navigator.of(context).pop(t),
              ),
          ],
        ),
      ),
    );
    if (picked != null && mounted) {
      setState(() {
        d.cutoff = picked;
        _errors.remove('cutoff');
      });
    }
  }

  Widget _error(String key) => _errors[key] == null
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Semantics(
            liveRegion: true,
            child: Text(
              _errors[key]!,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.error,
              ),
            ),
          ),
        );

  Widget _input(
    String key,
    String label,
    TextEditingController controller, {
    TextInputType? keyboard,
    List<TextInputFormatter>? formatters,
    TextCapitalization capitalization = TextCapitalization.none,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _Label(label),
        Semantics(
          label: label,
          child: TextField(
            controller: controller,
            enabled: !_busy,
            keyboardType: keyboard,
            inputFormatters: formatters,
            textCapitalization: capitalization,
            onChanged: (_) {
              if (_errors.containsKey(key)) {
                setState(() => _errors.remove(key));
              }
            },
          ),
        ),
        _error(key),
      ],
    ),
  );

  List<Widget> _detailsStep(AppLocalizations l) => [
    _input(
      'first',
      l.firstName,
      _first,
      capitalization: TextCapitalization.words,
    ),
    _input('last', l.lastName, _last, capitalization: TextCapitalization.words),
    _ReadOnly(
      label: l.email,
      value: widget.details.email,
      icon: Symbols.verified_rounded,
    ),
    const SizedBox(height: 16),
    _input('mobile', l.mobileNumber, _mobile, keyboard: TextInputType.phone),
  ];

  List<Widget> _societyStep(AppLocalizations l) => [
    _ReadOnly(label: l.society, value: widget.details.society),
    const SizedBox(height: 16),
    _ReadOnly(
      label: l.flat,
      value: widget.details.flat.isEmpty ? l.notOnFile : widget.details.flat,
    ),
    const SizedBox(height: 16),
    _Note(l.onlyPriveoCanChange),
  ];

  List<Widget> _vehicleStep(AppLocalizations l, _VehicleDraft d) {
    final v = d.vehicle;
    final price = v.monthlyPriceRupees;
    final preview = d.basement == null && d.number.text.trim().isEmpty
        ? null
        : '${d.basement ?? '–'} · ${d.number.text.trim().isEmpty ? '–' : d.number.text.trim()}';
    return [
      _ReadOnly(
        label: l.vehicle,
        value: v.model,
        detail: v.registration.isEmpty ? l.noRegistration : v.registration,
      ),
      const SizedBox(height: 8),
      _Note(l.onlyPriveoCanChange),
      const SizedBox(height: 24),
      const SectionLabel(AccountStrings.vehiclePhoto),
      const SizedBox(height: 12),
      VehiclePhotoField(
        key: ValueKey(v.id),
        vehicleId: v.id,
        reportDone: true,
        height: 90,
      ),
      _error('photo'),
      const SizedBox(height: 24),
      SectionLabel(l.parking),
      const SizedBox(height: 12),
      _Label(l.basement),
      _Choices(
        options: _basements,
        selected: d.basement,
        enabled: !_busy,
        onSelected: (b) => setState(() {
          d.basement = b;
          _errors.remove('basement');
        }),
      ),
      _error('basement'),
      const SizedBox(height: 16),
      _input(
        'number',
        l.parkingNumber,
        d.number,
        keyboard: TextInputType.number,
        formatters: [
          FilteringTextInputFormatter.digitsOnly,
          LengthLimitingTextInputFormatter(5),
        ],
      ),
      if (preview != null)
        Text(
          l.parkingPreview(preview),
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      if (v.hasSubscription) ...[
        const SizedBox(height: 24),
        SectionLabel(l.servicePreferences),
        const SizedBox(height: 12),
        _Label(l.cutoffTime),
        OutlinedButton.icon(
          onPressed: _busy ? null : () => _pickCutoff(d),
          icon: const Icon(Symbols.schedule_rounded, size: 18),
          label: Text(d.cutoff == null ? l.chooseTime : formatClock(d.cutoff!)),
        ),
        _error('cutoff'),
        const SizedBox(height: 8),
        _Note(l.cutoffNote),
        if (v.asksInteriorDay) ...[
          const SizedBox(height: 16),
          _Label(l.interiorCareDay),
          _Choices(
            options: _weekdays,
            selected: d.day,
            enabled: !_busy,
            short: true,
            onSelected: (day) => setState(() {
              d.day = day;
              _errors.remove('day');
            }),
          ),
          _error('day'),
        ],
        const SizedBox(height: 24),
        SectionLabel(l.plan),
        const SizedBox(height: 12),
        _ReadOnly(
          label: v.planName ?? l.yourPlan,
          value: price == null
              ? l.notOnFile
              : l.pricePerMonth(formatRupees(price)),
        ),
      ],
    ];
  }

  List<Widget> _reviewStep(AppLocalizations l) {
    final summary = ref.watch(onboardingSummaryProvider).value ?? [];
    Widget row(String label, String value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: context.brand.mute),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
    Widget section(String title, int step, List<Widget> rows) => Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: SectionCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: SectionLabel(title)),
                TextButton(
                  onPressed: _busy ? null : () => _show(step),
                  child: Text(l.edit),
                ),
              ],
            ),
            ...rows,
          ],
        ),
      ),
    );
    return [
      section(l.yourDetails, 0, [
        row(l.name, '${_first.text.trim()} ${_last.text.trim()}'),
        row(l.email, widget.details.email),
        row(l.mobileNumber, _mobile.text.trim()),
        row(l.society, widget.details.society),
        if (widget.details.flat.isNotEmpty) row(l.flat, widget.details.flat),
      ]),
      for (final v in summary)
        SectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${v['society']} · ${v['make']} ${v['model']} ${v['variant']}',
              ),
              if (v['plan'] is Map) ...[
                if (v['plan']['list_price_rupees'] != null)
                  Text(
                    '₹${v['plan']['list_price_rupees']}',
                    style: const TextStyle(
                      decoration: TextDecoration.lineThrough,
                    ),
                  ),
                Text('${v['plan']['badge']} · ${l.addVehicleCancel}'),
                for (final inclusion in v['plan']['inclusions'] as List)
                  Text('• $inclusion'),
              ],
              for (final p in v['payments'] as List)
                Text('₹${p['amount_rupees']} · ${p['status']}'),
              Text(l.addVehicleTotal),
              Text(l.addVehicleStartNote),
            ],
          ),
        ),
      for (final (i, d) in _drafts.indexed)
        section(d.vehicle.model, i + 2, [
          row(
            l.registration,
            d.vehicle.registration.isEmpty
                ? l.noRegistration
                : d.vehicle.registration,
          ),
          row(l.parking, '${d.basement}-${d.number.text.trim()}'),
          if (d.cutoff != null) row(l.cutoffTime, formatClock(d.cutoff!)),
          if (d.vehicle.asksInteriorDay && d.day != null)
            row(l.interiorCareDay, d.day!),
          if (d.vehicle.monthlyPriceRupees != null)
            row(
              l.plan,
              l.pricePerMonth(formatRupees(d.vehicle.monthlyPriceRupees!)),
            ),
        ]),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final (title, body) = switch (_step) {
      0 => (l.yourDetails, _detailsStep(l)),
      1 => (l.yourSociety, _societyStep(l)),
      _ when _onReview => (l.reviewAndConfirm, _reviewStep(l)),
      _ => (
        _drafts.length == 1
            ? l.yourVehicle
            : l.vehicleOf(_step - 1, _drafts.length),
        _vehicleStep(l, _drafts[_step - 2]),
      ),
    };
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 12, 0),
          child: Row(
            children: [
              Image.asset(
                'assets/brand/priveo-mark.png',
                height: 30,
                semanticLabel: l.appName,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  l.stepOf(_step + 1, _steps),
                  style: text.bodySmall?.copyWith(color: b.mute),
                ),
              ),
              const SignOutButton(),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: (_step + 1) / _steps,
              minHeight: 4,
              color: b.gold,
              backgroundColor: b.line,
            ),
          ),
        ),
        Expanded(
          child: ListView(
            controller: _scroll,
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
            children: [
              Text(title, style: text.headlineMedium),
              const SizedBox(height: 6),
              Text(
                _onReview ? l.reviewIntro : l.onboardingIntro,
                style: text.bodyMedium?.copyWith(color: b.mute),
              ),
              const SizedBox(height: 24),
              ...body,
            ],
          ),
        ),
        // Just above the buttons, so it is always on screen.
        if (_failure != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
            child: Semantics(
              liveRegion: true,
              child: Text(
                _failure!,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Theme.of(context).colorScheme.error,
                ),
              ),
            ),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 16),
          child: Row(
            children: [
              if (_step > 0) ...[
                OutlinedButton(
                  onPressed: _busy ? null : () => _show(_step - 1),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(96, 56),
                  ),
                  child: Text(l.back),
                ),
                const SizedBox(width: 12),
              ],
              Expanded(
                child: PrimaryButton(
                  label: _onReview
                      ? ((ref.watch(onboardingSummaryProvider).value ?? []).any(
                              (v) => (v['payments'] as List).any(
                                (p) =>
                                    p['status'] == 'Due' ||
                                    p['status'] == 'Over due',
                              ),
                            )
                            ? l.addVehicleConfirm
                            : l.confirmDetails)
                      : l.continueButton,
                  busy: _busy,
                  onPressed: _onReview ? _confirm : _continue,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Label extends StatelessWidget {
  const _Label(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: ExcludeSemantics(
      child: Text(
        text,
        style: Theme.of(
          context,
        ).textTheme.labelMedium?.copyWith(color: context.brand.mute),
      ),
    ),
  );
}

class _Note extends StatelessWidget {
  const _Note(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: Theme.of(
      context,
    ).textTheme.bodySmall?.copyWith(color: context.brand.mute),
  );
}

/// A detail the customer can see but not change here.
class _ReadOnly extends StatelessWidget {
  const _ReadOnly({
    required this.label,
    required this.value,
    this.detail,
    this.icon,
  });

  final String label;
  final String value;
  final String? detail;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return Semantics(
      label: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: b.line),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: text.labelSmall?.copyWith(color: b.mute)),
                  const SizedBox(height: 4),
                  Text(value, style: text.titleMedium),
                  if (detail != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      detail!,
                      style: text.bodySmall?.copyWith(color: b.mute),
                    ),
                  ],
                ],
              ),
            ),
            if (icon != null) Icon(icon, size: 20, color: b.ok, fill: 1),
          ],
        ),
      ),
    );
  }
}

/// A single choice from a few options, as pills.
class _Choices extends StatelessWidget {
  const _Choices({
    required this.options,
    required this.selected,
    required this.onSelected,
    required this.enabled,
    this.short = false,
  });

  final List<String> options;
  final String? selected;
  final ValueChanged<String> onSelected;
  final bool enabled;

  /// Shows the first three letters, as for weekdays.
  final bool short;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final o in options)
          Semantics(
            button: true,
            selected: o == selected,
            label: o,
            child: Material(
              color: o == selected
                  ? b.gold.withValues(alpha: 0.16)
                  : Colors.transparent,
              shape: StadiumBorder(
                side: BorderSide(color: o == selected ? b.gold : b.line),
              ),
              child: InkWell(
                customBorder: const StadiumBorder(),
                onTap: enabled ? () => onSelected(o) : null,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    minWidth: 56,
                    minHeight: 44,
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    child: Center(
                      widthFactor: 1,
                      heightFactor: 1,
                      child: ExcludeSemantics(
                        child: Text(
                          short ? o.substring(0, 3) : o,
                          style: Theme.of(context).textTheme.labelLarge
                              ?.copyWith(
                                color: o == selected ? b.goldHi : null,
                              ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
