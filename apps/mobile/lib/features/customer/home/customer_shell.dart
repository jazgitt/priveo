import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import 'customer_home_data.dart';

/// Customer shell: bottom tabs. Only Home has content in Phase 0.
class CustomerShell extends StatefulWidget {
  const CustomerShell({super.key});

  @override
  State<CustomerShell> createState() => _CustomerShellState();
}

class _CustomerShellState extends State<CustomerShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l.appName),
        actions: const [SignOutButton()],
      ),
      body: _index == 0 ? const CustomerHomeScreen() : const ComingSoon(),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          NavigationDestination(
              icon: const Icon(Icons.home_outlined), label: l.tabHome),
          NavigationDestination(
              icon: const Icon(Icons.calendar_month_outlined),
              label: l.tabCalendar),
          NavigationDestination(
              icon: const Icon(Icons.person_outline), label: l.tabAccount),
          NavigationDestination(
              icon: const Icon(Icons.support_agent_outlined),
              label: l.tabSupport),
        ],
      ),
    );
  }
}

class CustomerHomeScreen extends ConsumerWidget {
  const CustomerHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final home = ref.watch(customerHomeProvider);
    return home.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) =>
          ErrorView(onRetry: () => ref.invalidate(customerHomeProvider)),
      data: (h) => RefreshIndicator(
        onRefresh: () => ref.refresh(customerHomeProvider.future),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(l.hello(h.greetingName),
                style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 16),
            SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(h.vehicle.registration,
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(h.vehicle.model),
                  Text('${h.vehicle.society} · ${h.vehicle.parking}',
                      style: TextStyle(color: Theme.of(context).hintColor)),
                ],
              ),
            ),
            const SizedBox(height: 12),
            SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l.nextService,
                      style: Theme.of(context).textTheme.labelMedium),
                  const SizedBox(height: 6),
                  Text(formatDate(h.nextService.date),
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 2),
                  Text(h.nextService.service),
                  const SizedBox(height: 8),
                  StatusChip(h.nextService.status,
                      tone: StatusChip.toneFor(h.nextService.status)),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Text('${l.subscription}: '),
                StatusChip(h.subscriptionStatus,
                    tone: StatusChip.toneFor(h.subscriptionStatus)),
              ],
            ),
            const SizedBox(height: 16),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 2.2,
              children: [
                for (final a in h.quickActions)
                  OutlinedButton(
                    onPressed: () {},
                    child: Text(a.label, textAlign: TextAlign.center),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
