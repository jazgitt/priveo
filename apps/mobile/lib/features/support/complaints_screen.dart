import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import 'data/support_models.dart';
import 'data/support_repository.dart';
import 'routes.dart';
import 'support_strings.dart';
import 'widgets.dart';

ChipTone _tone(String status) => switch (status) {
      'Resolved' => ChipTone.ok,
      'In progress' => ChipTone.info,
      _ => ChipTone.warn,
    };

/// My complaints (CMP-01, CMP-02). Newest first.
class ComplaintsScreen extends ConsumerWidget {
  const ComplaintsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(complaintsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(t('support_complaints_title'))),
      body: list.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(context, e),
            onRetry: () => ref.invalidate(complaintsProvider)),
        data: (items) => RefreshIndicator(
          onRefresh: () => ref.refresh(complaintsProvider.future),
          child: items.isEmpty
              ? ListView(children: [
                  Padding(
                    padding: const EdgeInsets.all(32),
                    child: Center(child: Text(t('support_complaints_empty'))),
                  ),
                ])
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    for (final c in items) _ComplaintCard(c),
                  ],
                ),
        ),
      ),
    );
  }
}

class _ComplaintCard extends StatelessWidget {
  const _ComplaintCard(this.c);

  final Complaint c;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => context.push(SupportRoutes.complaint(c.id)),
        child: SectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: Text(c.displayId, style: theme.titleMedium)),
                  StatusChip(c.status, tone: _tone(c.status)),
                ],
              ),
              const SizedBox(height: 4),
              Text(c.category, style: theme.labelMedium),
              const SizedBox(height: 8),
              Text(c.description, maxLines: 2, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 8),
              LinearProgressIndicator(value: c.step / 3),
              const SizedBox(height: 8),
              Text(
                  t('support_complaint_raised_on',
                      {'date': formatDate(c.createdAt.toLocal())}),
                  style: theme.bodySmall),
              if (c.latestNote != null) ...[
                const SizedBox(height: 4),
                Text(c.latestNote!, style: theme.bodyMedium),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// One complaint with its thread, and a box to reply (back and forth with
/// the admin).
class ComplaintDetailScreen extends ConsumerStatefulWidget {
  const ComplaintDetailScreen({super.key, required this.id});

  final String id;

  @override
  ConsumerState<ComplaintDetailScreen> createState() =>
      _ComplaintDetailScreenState();
}

class _ComplaintDetailScreenState extends ConsumerState<ComplaintDetailScreen> {
  final _reply = TextEditingController();
  bool _busy = false;
  String? _failure;

  @override
  void dispose() {
    _reply.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final note = _reply.text.trim();
    if (note.isEmpty) return;
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      await ref.read(supportRepositoryProvider).reply(widget.id, note);
      _reply.clear();
      ref.invalidate(complaintProvider(widget.id));
      ref.invalidate(complaintsProvider);
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _failure = failureText(context, e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(complaintProvider(widget.id));
    final theme = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(detail.value?.displayId ?? '')),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(context, e),
            onRetry: () => ref.invalidate(complaintProvider(widget.id))),
        data: (c) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Row(
              children: [
                Expanded(child: Text(c.category, style: theme.titleMedium)),
                StatusChip(c.status, tone: _tone(c.status)),
              ],
            ),
            const SizedBox(height: 4),
            LinearProgressIndicator(value: c.step / 3),
            const SizedBox(height: 12),
            Text(c.description),
            const SizedBox(height: 4),
            Text(
                t('support_complaint_raised_on',
                    {'date': formatDate(c.createdAt.toLocal())}),
                style: theme.bodySmall),
            const SizedBox(height: 16),
            for (final u in c.updates) _Bubble(u),
            const SizedBox(height: 8),
            if (c.isResolved)
              Text(t('support_complaint_resolved'))
            else ...[
              TextField(
                controller: _reply,
                minLines: 1,
                maxLines: 4,
                decoration:
                    InputDecoration(labelText: t('support_complaint_reply_hint')),
              ),
              FormError(_failure),
              const SizedBox(height: 12),
              PrimaryButton(
                label: t('support_complaint_send'),
                busy: _busy,
                onPressed: _send,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble(this.u);

  final ThreadEntry u;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mine = u.fromCustomer;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        constraints: const BoxConstraints(maxWidth: 320),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(mine ? t('support_thread_you') : t('support_thread_priveo'),
                style: theme.textTheme.labelMedium),
            if (u.status != null)
              Text(t('support_status_changed', {'status': u.status!}),
                  style: theme.textTheme.titleSmall),
            if (u.note.isNotEmpty) Text(u.note),
            const SizedBox(height: 4),
            Text(formatDate(u.createdAt.toLocal()),
                style: theme.textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}
