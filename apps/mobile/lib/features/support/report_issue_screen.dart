import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import 'data/support_repository.dart';
import 'routes.dart';
import 'support_strings.dart';
import 'widgets.dart';

/// Report an issue (ISS-01 to ISS-06). [visitId] is the clean the customer
/// came from (ISS-02, SVC-08).
class ReportIssueScreen extends ConsumerStatefulWidget {
  const ReportIssueScreen({super.key, this.visitId});

  final String? visitId;

  @override
  ConsumerState<ReportIssueScreen> createState() => _ReportIssueScreenState();
}

class _ReportIssueScreenState extends ConsumerState<ReportIssueScreen> {
  final _description = TextEditingController();
  String? _category;
  String? _categoryError;
  String? _descriptionError;
  String? _failure;
  bool _busy = false;

  @override
  void dispose() {
    _description.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    setState(() {
      _categoryError =
          _category == null ? t('support_issue_choose') : null; // ISS-05
      _descriptionError = _description.text.trim().isEmpty
          ? t('support_issue_description_required')
          : null;
      _failure = null;
    });
    if (_categoryError != null || _descriptionError != null) return;
    setState(() => _busy = true);
    final messenger = ScaffoldMessenger.of(context);
    final router = GoRouter.of(context);
    try {
      await ref.read(supportRepositoryProvider).createComplaint(
            category: _category!,
            description: _description.text.trim(),
            visitId: widget.visitId,
          );
      ref.invalidate(complaintsProvider);
      ref.invalidate(supportContactProvider);
      messenger.showSnackBar(SnackBar(content: Text(t('support_issue_sent'))));
      // ISS-06: land on My complaints, newest first.
      router.pushReplacement(SupportRoutes.complaints);
    } catch (e) {
      if (mounted) {
        setState(() {
          _failure = failureText(context, e);
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final options = ref.watch(supportOptionsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(t('support_report_title'))),
      body: options.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(context, e),
            onRetry: () => ref.invalidate(supportOptionsProvider)),
        data: (o) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(t('support_issue_category'),
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                for (final c in o.issueCategories)
                  ChoiceChip(
                    label: Text(c),
                    selected: _category == c,
                    onSelected: (_) => setState(() {
                      _category = c;
                      _categoryError = null;
                    }),
                  ),
              ],
            ),
            FormError(_categoryError),
            if (widget.visitId != null) ...[
              const SizedBox(height: 16),
              Text(t('support_issue_linked_visit'),
                  style: Theme.of(context).textTheme.bodySmall),
            ],
            const SizedBox(height: 16),
            TextField(
              controller: _description,
              minLines: 4,
              maxLines: 8,
              maxLength: 2000,
              decoration: InputDecoration(
                labelText: t('support_issue_description'),
                errorText: _descriptionError,
              ),
            ),
            FormError(_failure),
            const SizedBox(height: 16),
            PrimaryButton(
              label: t('support_issue_send'),
              busy: _busy,
              onPressed: _send,
            ),
          ],
        ),
      ),
    );
  }
}
