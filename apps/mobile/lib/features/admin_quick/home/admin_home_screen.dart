import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import 'admin_home_data.dart';

class AdminHomeScreen extends ConsumerWidget {
  const AdminHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final home = ref.watch(adminHomeProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l.appName),
        actions: const [SignOutButton()],
      ),
      body: home.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            ErrorView(onRetry: () => ref.invalidate(adminHomeProvider)),
        data: (h) => RefreshIndicator(
          onRefresh: () => ref.refresh(adminHomeProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Row(
                children: [
                  _Stat(l.adminAlerts, h.alertCount),
                  const SizedBox(width: 12),
                  _Stat(l.adminNeedsScheduling, h.needsSchedulingCount),
                ],
              ),
              const SizedBox(height: 20),
              Text(l.adminPaymentsToConfirm,
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              if (h.paymentsToConfirm.isEmpty) Text(l.adminNoPayments),
              for (final p in h.paymentsToConfirm) ...[
                SectionCard(
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(p.customerLabel,
                                style: Theme.of(context).textTheme.titleSmall),
                            Text(p.reference),
                          ],
                        ),
                      ),
                      Text(formatRupees(p.amountRupees),
                          style: Theme.of(context).textTheme.titleMedium),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat(this.label, this.value);
  final String label;
  final int value;

  @override
  Widget build(BuildContext context) => Expanded(
        child: SectionCard(
          child: Column(
            children: [
              Text('$value', style: Theme.of(context).textTheme.headlineMedium),
              Text(label,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelMedium),
            ],
          ),
        ),
      );
}
