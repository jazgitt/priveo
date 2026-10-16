import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../core/ui/widgets.dart';
import 'data/support_repository.dart';
import 'feedback_sheet.dart';
import 'routes.dart';
import 'support_strings.dart';
import 'widgets.dart';

/// Help and support (SUP-01 to SUP-04, SUP-06).
class HelpScreen extends ConsumerWidget {
  const HelpScreen({super.key});

  Future<void> _open(BuildContext context, WidgetRef ref, Uri uri) async {
    final messenger = ScaffoldMessenger.of(context);
    var ok = false;
    try {
      ok = await ref.read(linkOpenerProvider)(uri);
    } catch (_) {
      ok = false;
    }
    if (!ok) {
      messenger.showSnackBar(SnackBar(content: Text(t('support_cannot_open'))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contact = ref.watch(supportContactProvider);
    final pending = ref.watch(pendingCheckInsProvider).value ?? const [];
    return Scaffold(
      appBar: AppBar(title: Text(t('support_title'))),
      body: contact.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(context, e),
            onRetry: () => ref.invalidate(supportContactProvider)),
        data: (c) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _Tile(
              icon: Symbols.call_rounded,
              label: t('support_call'),
              subtitle: c.helpline,
              onTap: () => _open(context, ref, Uri(scheme: 'tel', path: c.helpline)),
            ),
            _Tile(
              icon: Symbols.chat_rounded,
              label: t('support_whatsapp'),
              subtitle: c.whatsapp,
              onTap: () => _open(context, ref, whatsappUri(c.whatsapp)),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
              child: Text(t('support_hours', {'hours': c.hours}),
                  style: Theme.of(context).textTheme.bodySmall),
            ),
            const SizedBox(height: 8),
            _Tile(
              icon: Symbols.help_rounded,
              label: t('support_faq'),
              onTap: () => context.push(SupportRoutes.faq),
            ),
            _Tile(
              icon: Symbols.report_rounded,
              label: t('support_report_issue'),
              onTap: () => context.push(SupportRoutes.report),
            ),
            _Tile(
              icon: Symbols.forum_rounded,
              label: t('support_my_complaints'),
              subtitle: c.complaintsInProgress > 0
                  ? t('support_complaints_in_progress',
                      {'count': c.complaintsInProgress})
                  : null,
              onTap: () => context.push(SupportRoutes.complaints),
            ),
            _Tile(
              icon: Symbols.star_rounded,
              label: t('support_give_feedback'),
              onTap: () => showFeedbackSheet(context),
            ),
            if (pending.isNotEmpty)
              _Tile(
                icon: Symbols.fact_check_rounded,
                label: t('support_monthly_checkin'),
                subtitle: pending.first.vehicleLabel,
                onTap: () => context.push(SupportRoutes.checkin),
              ),
          ],
        ),
      ),
    );
  }
}

/// `https://wa.me/<digits>` for a number such as `+91 98765 43210`.
Uri whatsappUri(String number) =>
    Uri.parse('https://wa.me/${number.replaceAll(RegExp(r'[^0-9]'), '')}');

class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.subtitle,
  });

  final IconData icon;
  final String label;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Card(
          child: ListTile(
            leading: Icon(icon),
            title: Text(label),
            subtitle: subtitle == null ? null : Text(subtitle!),
            trailing: const Icon(Symbols.chevron_right_rounded),
            onTap: onTap,
          ),
        ),
      );
}
