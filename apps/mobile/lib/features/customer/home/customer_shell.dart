import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/api/api.g.dart';
import '../../../core/auth/auth_controller.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/tokens.g.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import '../../support/help_screen.dart';
import '../account/account_screen.dart';
import '../calendar/calendar_screen.dart';
import '../data/customer_reads_repository.dart';
import '../onboarding/onboarding_review_screen.dart';
import 'customer_home_data.dart';

/// Customer shell: bottom tabs Home, Calendar, Account and Support.
/// The layout follows the prototype's dark home.
class CustomerShell extends ConsumerStatefulWidget {
  const CustomerShell({super.key});

  @override
  ConsumerState<CustomerShell> createState() => _CustomerShellState();
}

class _CustomerShellState extends ConsumerState<CustomerShell> {
  static const _calendarTab = 1;
  static const _accountTab = 2;
  int _index = 0;

  void _go(int index) => setState(() => _index = index);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    // Home opens only after the customer has confirmed their details (ONB-25).
    final home = ref.watch(customerHomeProvider).value;
    if (home != null && !home.onboardingConfirmed) {
      return const OnboardingReviewScreen();
    }
    return Scaffold(
      extendBody: true,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _TopBar(onAvatar: () => _go(_accountTab)),
            Expanded(
              child: switch (_index) {
                0 => CustomerHomeScreen(onCalendar: () => _go(_calendarTab)),
                _calendarTab => const CalendarScreen(),
                _accountTab => const AccountScreen(),
                _ => const HelpScreen(),
              },
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

  static const _side = EdgeInsets.symmetric(horizontal: 20);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final home = ref.watch(customerHomeProvider);
    return home.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => ErrorView(
        message: e is ApiFailure ? e.message : null,
        onRetry: () => ref.invalidate(customerHomeProvider),
      ),
      data: (h) {
        final selected = selectedIndex(
          h.vehicles,
          ref.watch(selectedVehicleProvider),
        );
        final vehicle = h.vehicles.isEmpty ? null : h.vehicles[selected];
        return RefreshIndicator(
          onRefresh: () => ref.refresh(customerHomeProvider.future),
          child: ListView(
            // Leaves room for the tab bar, which floats over the list.
            padding: const EdgeInsets.only(top: 14, bottom: 110),
            children: [
              Padding(
                padding: _side,
                child: Text(
                  l.greeting,
                  style: text.bodyMedium?.copyWith(color: b.mute),
                ),
              ),
              Padding(
                padding: _side,
                child: Text(h.greetingName, style: text.displaySmall),
              ),
              const SizedBox(height: 18),
              if (vehicle == null)
                Padding(
                  padding: _side,
                  child: SectionCard(child: Text(l.noVehicles)),
                )
              else if (h.vehicles.length == 1)
                Padding(padding: _side, child: _VehicleCard(vehicle))
              else
                _VehicleCarousel(
                  vehicles: h.vehicles,
                  selected: selected,
                  onSelected: (i) => ref
                      .read(selectedVehicleProvider.notifier)
                      .select(h.vehicles[i].id),
                ),
              // A vehicle with no subscription has no daily service.
              if (vehicle != null && vehicle.subscriptionStatus != null) ...[
                const SizedBox(height: 14),
                Padding(
                  padding: _side,
                  child: _NextServiceCard(vehicle, onCalendar: onCalendar),
                ),
              ],
              const SizedBox(height: 24),
              Padding(padding: _side, child: SectionLabel(l.quickActions)),
              const SizedBox(height: 12),
              Padding(
                padding: _side,
                child: GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  padding: EdgeInsets.zero,
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 2.4,
                  children: [for (final a in h.quickActions) _QuickAction(a)],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// The customer's vehicles as cards to swipe through (HOME-07). The card in
/// the middle is the selected one. Its neighbours peek in from the sides,
/// smaller, dimmer and turned away a little.
class _VehicleCarousel extends StatefulWidget {
  const _VehicleCarousel({
    required this.vehicles,
    required this.selected,
    required this.onSelected,
  });

  final List<VehicleCard> vehicles;
  final int selected;
  final ValueChanged<int> onSelected;

  @override
  State<_VehicleCarousel> createState() => _VehicleCarouselState();
}

class _VehicleCarouselState extends State<_VehicleCarousel> {
  late final _controller = PageController(
    initialPage: widget.selected,
    viewportFraction: 0.86,
  );

  @override
  void didUpdateWidget(_VehicleCarousel old) {
    super.didUpdateWidget(old);
    // The selection changed somewhere else: follow it.
    if (_controller.hasClients &&
        _controller.page?.round() != widget.selected) {
      _controller.jumpToPage(widget.selected);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  double _distanceFrom(int index) {
    final page = _controller.hasClients && _controller.position.haveDimensions
        ? _controller.page ?? widget.selected.toDouble()
        : widget.selected.toDouble();
    return (page - index).clamp(-1.0, 1.0);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final b = context.brand;
    final flat = MediaQuery.disableAnimationsOf(context);
    // The card's content is a fixed number of text lines, so its height
    // follows the text size setting.
    final height = 90 + 82 * MediaQuery.textScalerOf(context).scale(1);
    return Column(
      children: [
        SizedBox(
          height: height,
          child: PageView.builder(
            controller: _controller,
            itemCount: widget.vehicles.length,
            onPageChanged: widget.onSelected,
            itemBuilder: (context, i) => AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                final d = _distanceFrom(i);
                final away = d.abs();
                return Opacity(
                  opacity: 1 - 0.45 * away,
                  child: Transform(
                    alignment: Alignment.center,
                    transform: Matrix4.identity()
                      ..setEntry(3, 2, 0.0012)
                      ..rotateY(flat ? 0 : d * 0.32)
                      ..scaleByDouble(1 - 0.07 * away, 1 - 0.07 * away, 1, 1),
                    child: child,
                  ),
                );
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 5),
                child: _VehicleCard(widget.vehicles[i]),
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        Semantics(
          label: l.vehicleOf(widget.selected + 1, widget.vehicles.length),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (var i = 0; i < widget.vehicles.length; i++)
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  width: i == widget.selected ? 18 : 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: i == widget.selected ? b.gold : b.line,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Number plate, model, society, parking and the plan price, with the
/// subscription status.
class _VehicleCard extends StatelessWidget {
  const _VehicleCard(this.vehicle);

  final VehicleCard vehicle;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final status = vehicle.subscriptionStatus;
    final price = vehicle.monthlyPriceRupees;
    Widget line(IconData icon, String value) => Row(
      children: [
        Icon(icon, size: 15, color: b.mute),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: text.bodySmall?.copyWith(color: b.mute),
          ),
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
              Expanded(
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: vehicle.registration.isEmpty
                          ? b.line
                          : DarkTokens.text,
                      borderRadius: BorderRadius.circular(7),
                    ),
                    child: Text(
                      vehicle.registration.isEmpty
                          ? l.noRegistration
                          : vehicle.registration,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: text.labelMedium?.copyWith(
                        color: vehicle.registration.isEmpty
                            ? b.mute
                            : const Color(0xFF111111),
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Semantics(
                label: l.subscription,
                child: StatusChip(
                  status ?? l.noSubscription,
                  tone: status == null
                      ? ChipTone.neutral
                      : StatusChip.toneFor(status),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            vehicle.model,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: text.titleLarge,
          ),
          const SizedBox(height: 12),
          line(Symbols.location_on_rounded, vehicle.society),
          const SizedBox(height: 4),
          line(
            Symbols.local_parking_rounded,
            vehicle.parking.isEmpty ? l.noParking : vehicle.parking,
          ),
          const SizedBox(height: 4),
          line(
            Symbols.workspace_premium_rounded,
            price == null ? l.noPlan : l.pricePerMonth(formatRupees(price)),
          ),
        ],
      ),
    );
  }
}

/// The next visit for the selected vehicle (HOME-04). Until visits are
/// scheduled it shows the customer's service time and interior care day.
class _NextServiceCard extends ConsumerWidget {
  const _NextServiceCard(this.vehicle, {required this.onCalendar});

  final VehicleCard vehicle;
  final VoidCallback onCalendar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    // The home data has no visit yet: ask the customer reads for it.
    final fromVisits = ref
        .watch(nextServicesProvider)
        .value
        ?.where((n) => n.vehicleId == vehicle.id)
        .firstOrNull;
    final next =
        vehicle.nextService ??
        (fromVisits == null
            ? null
            : NextService(
                date: fromVisits.date,
                service: fromVisits.service,
                status: fromVisits.status,
              ));
    final cutoff = vehicle.cutoffTime;
    final day = vehicle.interiorDay;
    Widget detail(String service, String value) => Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        children: [
          _ServiceMarker(service),
          const SizedBox(width: 8),
          Expanded(
            child: Text(value, style: text.bodyMedium?.copyWith(color: b.mute)),
          ),
        ],
      ),
    );
    return SectionCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: SectionLabel(l.nextService)),
              if (next != null)
                StatusChip(next.status, tone: StatusChip.toneFor(next.status)),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            next == null ? l.notScheduledYet : formatDate(next.date),
            style: text.headlineSmall,
          ),
          if (next != null && next.service.isNotEmpty)
            detail(next.service, next.service),
          if (cutoff != null)
            detail('Cleaning-External', l.dailyCleanBy(formatClock(cutoff))),
          if (day != null) detail('Cleaning-Internal', l.interiorCareOn(day)),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onCalendar,
              icon: const Icon(Symbols.calendar_month_rounded, size: 18),
              label: Text(l.viewCalendar),
            ),
          ),
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
