import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import 'data/support_models.dart';
import 'data/support_repository.dart';
import 'support_strings.dart';
import 'widgets.dart';

/// The monthly check-in (CHK-02 to CHK-07). With no [subscriptionId] it opens
/// the first check-in that is due.
class CheckInScreen extends ConsumerStatefulWidget {
  const CheckInScreen({super.key, this.subscriptionId});

  final String? subscriptionId;

  @override
  ConsumerState<CheckInScreen> createState() => _CheckInScreenState();
}

class _CheckInScreenState extends ConsumerState<CheckInScreen> {
  final _comment = TextEditingController();
  final Map<String, int> _ratings = {};
  bool _busy = false;
  bool _done = false;
  String? _failure;

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  Future<void> _submit(PendingCheckIn due) async {
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      await ref.read(supportRepositoryProvider).submitCheckIn(
            due.subscriptionId,
            Map.of(_ratings),
            _comment.text.trim(),
          );
      ref.invalidate(pendingCheckInsProvider); // CHK-08: the Home card goes.
      if (mounted) {
        setState(() {
          _busy = false;
          _done = true;
        });
      }
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
    final pending = ref.watch(pendingCheckInsProvider);
    final options = ref.watch(supportOptionsProvider);
    final theme = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(t('support_checkin_title'))),
      body: Builder(builder: (context) {
        if (_done) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(t('support_checkin_thanks'),
                      textAlign: TextAlign.center, style: theme.titleMedium),
                  const SizedBox(height: 16),
                  OutlinedButton(
                    onPressed: () => context.canPop() ? context.pop() : null,
                    child: Text(MaterialLocalizations.of(context).closeButtonLabel),
                  ),
                ],
              ),
            ),
          );
        }
        if (pending.isLoading || options.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        final error = pending.error ?? options.error;
        if (error != null) {
          return ErrorView(
            message: failureText(context, error),
            onRetry: () {
              ref.invalidate(pendingCheckInsProvider);
              ref.invalidate(supportOptionsProvider);
            },
          );
        }
        final due = pending.requireValue
            .where((p) =>
                widget.subscriptionId == null ||
                p.subscriptionId == widget.subscriptionId)
            .firstOrNull;
        if (due == null) {
          return Center(child: Text(t('support_checkin_none')));
        }
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(t('support_checkin_intro', {'vehicle': due.vehicleLabel})),
            const SizedBox(height: 16),
            for (final c in options.requireValue.checkinCategories)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(c.name, style: theme.titleSmall),
                    if (c.description.isNotEmpty)
                      Text(c.description, style: theme.bodySmall),
                    StarRating(
                      value: _ratings[c.name] ?? 0,
                      allowClear: true, // CHK-02: a category may stay unrated.
                      onChanged: (n) => setState(() {
                        if (n == 0) {
                          _ratings.remove(c.name);
                        } else {
                          _ratings[c.name] = n;
                        }
                      }),
                    ),
                  ],
                ),
              ),
            TextField(
              controller: _comment,
              minLines: 2,
              maxLines: 5,
              maxLength: 1000,
              decoration: InputDecoration(labelText: t('support_checkin_comment')),
            ),
            FormError(_failure),
            const SizedBox(height: 12),
            PrimaryButton(
              label: t('support_checkin_submit'),
              busy: _busy,
              // CHK-07: at least one category rated.
              onPressed: _ratings.isEmpty ? null : () => _submit(due),
            ),
          ],
        );
      }),
    );
  }
}
