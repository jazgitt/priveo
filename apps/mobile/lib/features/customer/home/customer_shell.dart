import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/api/api.g.dart';
import '../../../core/auth/auth_controller.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/tokens.g.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import 'customer_home_data.dart';

/// Customer shell: bottom tabs. Only Home has content in Phase 0.
/// The layout follows the prototype's dark home.
class CustomerShell extends StatefulWidget {
  const CustomerShell({super.key});

  @override
  State<CustomerShell> createState() => _CustomerShellState();
}

class _CustomerShellState extends State<CustomerShell> {
  static const _calendarTab = 1;
  static const _accountTab = 2;
  int _index = 0;

  void _go(int index) => setState(() => _index = index);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      extendBody: true,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _TopBar(onAvatar: () => _go(_accountTab)),
            Expanded(
              child: _index == 0
                  ? CustomerHomeScreen(onCalendar: () => _go(_calendarTab))
                  : const ComingSoon(),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _TabBar(
        index: _index,
        onSelected: _go,
        tabs: [
          (Symbols.home_rounded, l.tabHome),
          (Symbols.calendar_month_rounded, l.tabCalendar),
          (Symbols.person_rounded, l.tabAccount),
          (Symbols.support_agent_rounded, l.tabSupport),
        ],
      ),
    );
  }
}

/// The P mark on the left, sign-out and the round avatar on the right.
class _TopBar extends ConsumerWidget {
  const _TopBar({required this.onAvatar});

  final VoidCallback onAvatar;

  static String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty);
    return parts.take(2).map((p) => p[0].toUpperCase()).join();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final name = ref.watch(authControllerProvider).value?.displayName ?? '';
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 12, 4),
      child: Row(
        children: [
          Image.asset(
            'assets/brand/priveo-mark.png',
            height: 30,
            semanticLabel: l.appName,
          ),
          const Spacer(),
          const SignOutButton(),
          const SizedBox(width: 4),
          Semantics(
            button: true,
            label: l.tabAccount,
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: onAvatar,
              child: Container(
                width: 42,
                height: 42,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: const LinearGradient(
                    colors: ButtonTokens.wineGradient,
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  border: Border.all(
                    color: context.brand.goldHi.withValues(alpha: 0.35),
                  ),
                ),
                child: ExcludeSemantics(
                  child: Text(
                    _initials(name),
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
        ],
      ),
    );
  }
}

/// A translucent bar with a top line. The selected tab is gold.
class _TabBar extends StatelessWidget {
  const _TabBar({
    required this.index,
    required this.onSelected,
    required this.tabs,
  });

  final int index;
  final ValueChanged<int> onSelected;
  final List<(IconData, String)> tabs;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: Container(
          decoration: BoxDecoration(
            color: Theme.of(
              context,
            ).scaffoldBackgroundColor.withValues(alpha: 0.88),
            border: Border(top: BorderSide(color: b.line)),
          ),
          child: SafeArea(
            top: false,
            child: SizedBox(
              height: 62,
              child: Row(
                children: [
                  for (final (i, (icon, label)) in tabs.indexed)
                    Expanded(
                      child: Semantics(
                        button: true,
                        selected: i == index,
                        child: InkWell(
                          onTap: () => onSelected(i),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(icon, color: i == index ? b.goldHi : b.dim),
                              const SizedBox(height: 4),
                              Text(
                                label,
                                style: Theme.of(context).textTheme.labelSmall
                                    ?.copyWith(
                                      color: i == index ? b.goldHi : b.dim,
                                    ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class CustomerHomeScreen extends ConsumerWidget {
  const CustomerHomeScreen({super.key, required this.onCalendar});

  final VoidCallback onCalendar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final home = ref.watch(customerHomeProvider);
    return home.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) =>
          ErrorView(onRetry: () => ref.invalidate(customerHomeProvider)),
      data: (h) => RefreshIndicator(
        onRefresh: () => ref.refresh(customerHomeProvider.future),
        child: ListView(
          // Leaves room for the tab bar, which floats over the list.
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 110),
          children: [
            Text(l.greeting, style: text.bodyMedium?.copyWith(color: b.mute)),
            Text(h.greetingName, style: text.displaySmall),
            const SizedBox(height: 18),
            _VehicleCard(h.vehicle, subscriptionStatus: h.subscriptionStatus),
            const SizedBox(height: 14),
            SectionCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: SectionLabel(l.nextService)),
                      StatusChip(
                        h.nextService.status,
                        tone: StatusChip.toneFor(h.nextService.status),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    formatDate(h.nextService.date),
                    style: text.headlineSmall,
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      _ServiceMarker(h.nextService.service),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          h.nextService.service,
                          style: text.bodyMedium?.copyWith(color: b.mute),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: onCalendar,
                      icon: const Icon(
                        Symbols.calendar_month_rounded,
                        size: 18,
                      ),
                      label: Text(l.viewCalendar),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            SectionLabel(l.quickActions),
            const SizedBox(height: 12),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              padding: EdgeInsets.zero,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 2.4,
              children: [for (final a in h.quickActions) _QuickAction(a)],
            ),
          ],
        ),
      ),
    );
  }
}

/// Number plate, model, society and parking, with the subscription status.
class _VehicleCard extends StatelessWidget {
  const _VehicleCard(this.vehicle, {required this.subscriptionStatus});

  final VehicleCard vehicle;
  final String subscriptionStatus;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    Widget line(IconData icon, String value) => Row(
      children: [
        Icon(icon, size: 15, color: b.mute),
        const SizedBox(width: 6),
        Expanded(
          child: Text(value, style: text.bodySmall?.copyWith(color: b.mute)),
        ),
      ],
    );
    return SectionCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: DarkTokens.text,
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Text(
                  vehicle.registration,
                  style: text.labelMedium?.copyWith(
                    color: const Color(0xFF111111),
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
              ),
              const Spacer(),
              Semantics(
                label: l.subscription,
                child: StatusChip(
                  subscriptionStatus,
                  tone: StatusChip.toneFor(subscriptionStatus),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(vehicle.model, style: text.titleLarge),
          const SizedBox(height: 12),
          line(Symbols.location_on_rounded, vehicle.society),
          const SizedBox(height: 4),
          line(Symbols.local_parking_rounded, vehicle.parking),
        ],
      ),
    );
  }
}

/// The prototype's service markers: a green dot for exterior, a blue square
/// for interior, a violet star for Deep Spa.
class _ServiceMarker extends StatelessWidget {
  const _ServiceMarker(this.service);

  final String service;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final s = service.toLowerCase();
    if (s.contains('spa')) {
      return Icon(Symbols.star_rounded, size: 12, color: b.spa, fill: 1);
    }
    final interior = s.contains('internal') || s.contains('interior');
    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        color: interior ? b.info : b.ok,
        borderRadius: BorderRadius.circular(interior ? 2 : 4),
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction(this.action);

  final QuickAction action;

  static IconData _iconFor(String key) => switch (key) {
    'skip_pause' => Symbols.pause_circle_rounded,
    'history' => Symbols.history_rounded,
    'feedback' => Symbols.star_rounded,
    'report_issue' => Symbols.report_rounded,
    _ => Symbols.arrow_forward_rounded,
  };

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final radius = BorderRadius.circular(18);
    return Material(
      color: Theme.of(context).colorScheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: BorderSide(color: b.line),
      ),
      child: InkWell(
        borderRadius: radius,
        onTap: () {},
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: b.gold.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: Icon(_iconFor(action.key), size: 18, color: b.gold),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  action.label,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    height: 1.2,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
