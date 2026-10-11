import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth_controller.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import '../alerts/routes.dart' show AlertsRoutes;
import '../payments/routes.dart' show adminAlertsPath, adminPaymentsPath;
import '../admin_quick_strings.dart';
import '../routes_paths.dart';
import 'admin_home_data.dart';

class AdminHomeScreen extends ConsumerWidget {
  const AdminHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final home = ref.watch(adminHomeProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.appName), actions: const [SignOutButton()]),
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
                  const SizedBox(width: 12),
                  _Stat(
                    q('adminq_home_open_complaints'),
                    h.openComplaintsCount,
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                l.adminPaymentsToConfirm,
                style: Theme.of(context).textTheme.titleLarge,
              ),
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
                            Text(
                              p.customerLabel,
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                            Text(p.reference),
                          ],
                        ),
                      ),
                      Text(
                        formatRupees(p.amountRupees),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
              ],
              if (h.paymentsToConfirmCount > h.paymentsToConfirm.length)
                Text(
                  q('adminq_home_more_payments', {
                    'count':
                        h.paymentsToConfirmCount - h.paymentsToConfirm.length,
                  }),
                ),
              const SizedBox(height: 12),
              for (final e in [
                (q('adminq_home_complaints'), AdminQuickPaths.complaints),
                (q('adminq_home_feedback'), AdminQuickPaths.feedback),
                (
                  q('adminq_home_needs_scheduling'),
                  AdminQuickPaths.needsScheduling,
                ),
                (q('adminq_home_day'), AdminQuickPaths.day),
                (q('adminq_home_capacity'), AdminQuickPaths.capacity),
              ]) ...[
                OutlinedButton(
                  onPressed: () => context.push(e.$2),
                  child: Text(e.$1),
                ),
                const SizedBox(height: 8),
              ],
              OutlinedButton(
                onPressed: () => context.push(adminPaymentsPath),
                child: const Text('All payments'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () => context.push(AlertsRoutes.alerts),
                child: Text(l.adminAlerts),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () => context.push(adminAlertsPath),
                child: const Text('Payment alerts'),
              ),
              const SizedBox(height: 12),
              const _SignOutAllButton(),
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
          Text(
            label,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.labelMedium,
          ),
        ],
      ),
    ),
  );
}

/// Ends every session of the admin's login, after asking once (ADM-ACC-14).
class _SignOutAllButton extends ConsumerWidget {
  const _SignOutAllButton();

  Future<void> _confirm(BuildContext context, WidgetRef ref) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(l.signOutAll),
        content: Text(l.signOutAllBody),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: Text(l.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(c, true),
            child: Text(l.signOut),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await ref.read(authControllerProvider.notifier).logoutAll();
    } on ApiFailure catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text(e.message ?? l.networkError)),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => OutlinedButton(
    onPressed: () => _confirm(context, ref),
    child: Text(AppLocalizations.of(context).signOutAll),
  );
}
