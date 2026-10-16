import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/read_refresh.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../support/widgets.dart' show failureText;
import '../admin_quick_strings.dart';
import '../data/admin_quick_models.dart';
import '../data/admin_quick_providers.dart';
import '../data/admin_quick_repository.dart';
import '../routes_paths.dart';

const _statuses = ['Raised', 'In progress', 'Resolved'];

String statusLabel(String status) => switch (status) {
  'Raised' => q('adminq_status_raised'),
  'In progress' => q('adminq_status_in_progress'),
  'Resolved' => q('adminq_status_resolved'),
  _ => status,
};

/// The complaints with a status filter (MQ-1, ADM-CMP).
class AdminComplaintsScreen extends ConsumerStatefulWidget {
  const AdminComplaintsScreen({super.key});

  @override
  ConsumerState<AdminComplaintsScreen> createState() =>
      _AdminComplaintsScreenState();
}

class _AdminComplaintsScreenState extends ConsumerState<AdminComplaintsScreen> {
  String _status = '';

  @override
  Widget build(BuildContext context) {
    final list = ref.watch(complaintsProvider(_status));
    return Scaffold(
      appBar: AppBar(title: Text(q('adminq_complaints_title'))),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Wrap(
              spacing: 8,
              children: [
                for (final s in ['', ..._statuses])
                  ChoiceChip(
                    label: Text(
                      s.isEmpty ? q('adminq_filter_all') : statusLabel(s),
                    ),
                    selected: _status == s,
                    onSelected: (_) => setState(() => _status = s),
                  ),
              ],
            ),
          ),
          Expanded(
            child: list.when(
              skipLoadingOnReload: true,
              skipError: true,
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => ErrorView(
                message: failureText(context, e),
                onRetry: () => ref.invalidate(complaintsProvider(_status)),
              ),
              data: (rows) => RefreshIndicator(
                onRefresh: () => refreshAll(
                  ref,
                  () => ref.read(complaintsProvider(_status).future),
                ),
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    if (rows.isEmpty) Text(q('adminq_complaints_empty')),
                    for (final c in rows)
                      Card(
                        child: ListTile(
                          title: Text('${c.displayId}  ${c.category}'),
                          subtitle: Text(
                            [
                              c.description,
                              [
                                c.customerName,
                                c.flat,
                                c.society,
                              ].where((e) => e.isNotEmpty).join(', '),
                              if (c.overdue) q('adminq_complaint_overdue'),
                            ].where((e) => e.isNotEmpty).join('\n'),
                          ),
                          isThreeLine: true,
                          trailing: Text(statusLabel(c.status)),
                          onTap: () =>
                              context.push(AdminQuickPaths.complaint(c.id)),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// One complaint: the thread, a status change and a note (ADM-CMP-03, 07).
class AdminComplaintScreen extends ConsumerStatefulWidget {
  const AdminComplaintScreen({super.key, required this.id});

  final String id;

  @override
  ConsumerState<AdminComplaintScreen> createState() =>
      _AdminComplaintScreenState();
}

class _AdminComplaintScreenState extends ConsumerState<AdminComplaintScreen> {
  final _note = TextEditingController();
  String? _status;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _run(Future<QuickComplaint> Function() call) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final messenger = ScaffoldMessenger.of(context);
    try {
      await call();
      ref.invalidate(complaintProvider(widget.id));
      ref.invalidate(complaintsProvider);
      ref.invalidate(adminQuickHomeProvider);
      _note.clear();
      messenger.showSnackBar(
        SnackBar(content: Text(q('adminq_complaint_saved'))),
      );
    } catch (e) {
      if (mounted) setState(() => _error = failureText(context, e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(complaintProvider(widget.id));
    final repo = ref.watch(adminQuickRepositoryProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(detail.value?.displayId ?? q('adminq_complaints_title')),
      ),
      body: detail.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(context, e),
          onRetry: () => ref.invalidate(complaintProvider(widget.id)),
        ),
        data: (c) {
          final status = _status ?? c.status;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      c.category,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      [
                        c.customerName,
                        c.flat,
                        c.society,
                      ].where((e) => e.isNotEmpty).join(', '),
                    ),
                    Text(
                      q('adminq_complaint_raised_on', {
                        'date': formatDate(c.createdAt.toLocal()),
                      }),
                    ),
                    if (c.overdue) Text(q('adminq_complaint_overdue')),
                    const SizedBox(height: 8),
                    Text(c.description),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Text(
                q('adminq_complaint_status'),
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  for (final s in _statuses)
                    ChoiceChip(
                      label: Text(statusLabel(s)),
                      selected: status == s,
                      onSelected: _busy
                          ? null
                          : (_) => setState(() => _status = s),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _note,
                maxLines: 3,
                maxLength: 1000,
                decoration: InputDecoration(
                  hintText: q('adminq_complaint_note_hint'),
                ),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () {
                              final note = _note.text.trim();
                              if (note.isEmpty) {
                                setState(
                                  () => _error = q(
                                    'adminq_complaint_note_required',
                                  ),
                                );
                                return;
                              }
                              _run(() => repo.addNote(c.id, note));
                            },
                      child: Text(q('adminq_complaint_add_note')),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton(
                      onPressed: _busy || status == c.status
                          ? null
                          : () => _run(
                              () => repo.setStatus(
                                c.id,
                                status,
                                _note.text.trim(),
                              ),
                            ),
                      child: Text(q('adminq_complaint_save_status')),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                q('adminq_complaint_thread'),
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              for (final u in c.updates)
                Card(
                  child: ListTile(
                    title: Text(
                      u.authorRole == 'customer'
                          ? q('adminq_complaint_by_customer')
                          : q('adminq_complaint_by_admin'),
                    ),
                    subtitle: Text(
                      [
                        if (u.note.isNotEmpty) u.note,
                        if (u.status != null)
                          q('adminq_complaint_status_changed', {
                            'status': statusLabel(u.status!),
                          }),
                        formatDate(u.createdAt.toLocal()),
                      ].join('\n'),
                    ),
                    isThreeLine: u.note.isNotEmpty,
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

/// Feedback with a rating filter, and the average of the visit ratings
/// (MQ-1, ADM-FDB). A rating is general to the visit, never to a crew member.
class AdminFeedbackScreen extends ConsumerStatefulWidget {
  const AdminFeedbackScreen({super.key});

  @override
  ConsumerState<AdminFeedbackScreen> createState() =>
      _AdminFeedbackScreenState();
}

class _AdminFeedbackScreenState extends ConsumerState<AdminFeedbackScreen> {
  int _rating = 0;

  @override
  Widget build(BuildContext context) {
    final list = ref.watch(feedbackProvider(_rating));
    final ratings = ref.watch(ratingsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(q('adminq_feedback_title'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            q('adminq_feedback_ratings'),
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 4),
          ratings.when(
            skipLoadingOnReload: true,
            skipError: true,
            loading: () => const LinearProgressIndicator(),
            error: (e, _) => Text(failureText(context, e)),
            data: (r) => Text(
              r.average == null
                  ? q('adminq_feedback_no_ratings')
                  : q('adminq_feedback_average', {
                      'average': r.average!.toStringAsFixed(1),
                      'count': r.count,
                    }),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              for (final n in [0, 5, 4, 3, 2, 1])
                ChoiceChip(
                  label: Text(
                    n == 0
                        ? q('adminq_filter_all')
                        : q('adminq_feedback_stars', {'n': n}),
                  ),
                  selected: _rating == n,
                  onSelected: (_) => setState(() => _rating = n),
                ),
            ],
          ),
          const SizedBox(height: 12),
          list.when(
            skipLoadingOnReload: true,
            skipError: true,
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => ErrorView(
              message: failureText(context, e),
              onRetry: () => ref.invalidate(feedbackProvider(_rating)),
            ),
            data: (rows) => Column(
              children: [
                if (rows.isEmpty) Text(q('adminq_feedback_empty')),
                for (final f in rows)
                  Card(
                    child: ListTile(
                      title: Text(
                        [
                          if (f.rating != null)
                            q('adminq_feedback_stars', {'n': f.rating!}),
                          if (f.category != null) f.category!,
                        ].join(', '),
                      ),
                      subtitle: Text(
                        [
                          if (f.comment.isNotEmpty) f.comment,
                          [
                            f.customerName,
                            f.society,
                            formatDate(f.createdAt.toLocal()),
                          ].where((e) => e.isNotEmpty).join(', '),
                        ].join('\n'),
                      ),
                      isThreeLine: f.comment.isNotEmpty,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
