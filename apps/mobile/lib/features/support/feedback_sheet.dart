import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ui/widgets.dart';
import 'data/support_models.dart';
import 'data/support_repository.dart';
import 'support_strings.dart';
import 'widgets.dart';

/// The feedback modal (FDBK-02 to FDBK-07). The side tab (FDBK-01) and the
/// Support screen both open it.
Future<void> showFeedbackSheet(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => const _SheetFrame(child: FeedbackForm()),
    );

/// Rates one visit as a whole (SVC-07, SVC-11, SVC-12, SVC-14, SVC-15). The
/// rating is general to the visit and is not given to any crew member.
Future<void> showVisitRatingSheet(BuildContext context, String visitId) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _SheetFrame(child: VisitRatingForm(visitId: visitId)),
    );

class _SheetFrame extends StatelessWidget {
  const _SheetFrame({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          top: 16,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: SingleChildScrollView(child: child),
      );
}

class _OptionChips extends StatelessWidget {
  const _OptionChips({
    required this.items,
    required this.selected,
    required this.onToggle,
  });

  final List<OptionItem> items;
  final Set<String> selected;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 8,
        children: [
          for (final o in items)
            Tooltip(
              message: o.description,
              child: FilterChip(
                label: Text(o.name),
                selected: selected.contains(o.name),
                onSelected: (_) => onToggle(o.name),
              ),
            ),
        ],
      );
}

class FeedbackForm extends ConsumerStatefulWidget {
  const FeedbackForm({super.key});

  @override
  ConsumerState<FeedbackForm> createState() => _FeedbackFormState();
}

class _FeedbackFormState extends ConsumerState<FeedbackForm> {
  final _comment = TextEditingController();
  String? _category;
  int _rating = 0;
  bool _testimonial = false; // FDBK-05: off by default.
  bool _busy = false;
  String? _failure;

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  // FDBK-07: a rating or a comment. A category alone is not enough.
  bool get _canSend => _rating > 0 || _comment.text.trim().isNotEmpty;

  Future<void> _send() async {
    setState(() {
      _busy = true;
      _failure = null;
    });
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      await ref.read(supportRepositoryProvider).sendFeedback(
            category: _category,
            rating: _rating == 0 ? null : _rating,
            comment: _comment.text.trim(),
            testimonial: _testimonial,
          );
      messenger
          .showSnackBar(SnackBar(content: Text(t('support_feedback_thanks'))));
      navigator.pop();
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
    final options = ref.watch(supportOptionsProvider).value;
    final theme = Theme.of(context).textTheme;
    final selectedHelp = options?.feedbackCategories
        .where((c) => c.name == _category)
        .map((c) => c.description)
        .firstOrNull;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(t('support_feedback_title'), style: theme.titleLarge),
        const SizedBox(height: 16),
        Text(t('support_feedback_rating'), style: theme.titleSmall),
        StarRating(value: _rating, onChanged: (n) => setState(() => _rating = n)),
        const SizedBox(height: 12),
        Text(t('support_feedback_category'), style: theme.titleSmall),
        const SizedBox(height: 8),
        if (options != null)
          _OptionChips(
            items: options.feedbackCategories,
            selected: {?_category},
            onToggle: (name) =>
                setState(() => _category = _category == name ? null : name),
          ),
        if (selectedHelp != null && selectedHelp.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(selectedHelp, style: theme.bodySmall),
          ),
        const SizedBox(height: 12),
        TextField(
          controller: _comment,
          minLines: 3,
          maxLines: 6,
          maxLength: 1000,
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(labelText: t('support_feedback_comment')),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: _testimonial,
          onChanged: (v) => setState(() => _testimonial = v ?? false),
          title: Text(t('support_feedback_testimonial')),
        ),
        FormError(_failure),
        const SizedBox(height: 12),
        PrimaryButton(
          label: t('support_feedback_send'),
          busy: _busy,
          onPressed: _canSend ? _send : null,
        ),
      ],
    );
  }
}

class VisitRatingForm extends ConsumerStatefulWidget {
  const VisitRatingForm({super.key, required this.visitId});

  final String visitId;

  @override
  ConsumerState<VisitRatingForm> createState() => _VisitRatingFormState();
}

class _VisitRatingFormState extends ConsumerState<VisitRatingForm> {
  final _comment = TextEditingController();
  int _rating = 0;
  final Set<String> _tags = {};
  bool _testimonial = false; // SVC-15: off by default.
  bool _busy = false;
  String? _failure;

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    setState(() {
      _busy = true;
      _failure = null;
    });
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      await ref.read(supportRepositoryProvider).rateVisit(
            widget.visitId,
            rating: _rating,
            tags: _tags.toList(),
            comment: _comment.text.trim(),
            testimonial: _testimonial,
          );
      messenger.showSnackBar(SnackBar(content: Text(t('support_rate_thanks'))));
      navigator.pop();
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
    final options = ref.watch(supportOptionsProvider).value;
    final theme = Theme.of(context).textTheme;
    // At 5 stars the positive tags, below it the issue tags (SVC-11, SVC-14).
    final tags = _rating == 0 || options == null
        ? const <OptionItem>[]
        : _rating == 5
            ? options.positiveTags
            : options.feedbackCategories;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(t('support_rate_title'), style: theme.titleLarge),
        const SizedBox(height: 12),
        StarRating(
          value: _rating,
          size: 44,
          onChanged: (n) => setState(() {
            if ((_rating == 5) != (n == 5)) _tags.clear();
            _rating = n;
          }),
        ),
        if (tags.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
              _rating == 5
                  ? t('support_rate_positive_tags')
                  : t('support_rate_issue_tags'),
              style: theme.titleSmall),
          const SizedBox(height: 8),
          _OptionChips(
            items: tags,
            selected: _tags,
            onToggle: (name) => setState(() {
              if (!_tags.add(name)) _tags.remove(name);
            }),
          ),
        ],
        const SizedBox(height: 12),
        TextField(
          controller: _comment,
          minLines: 2,
          maxLines: 5,
          maxLength: 1000,
          decoration: InputDecoration(labelText: t('support_feedback_comment')),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: _testimonial,
          onChanged: (v) => setState(() => _testimonial = v ?? false),
          title: Text(t('support_feedback_testimonial')),
        ),
        FormError(_failure),
        const SizedBox(height: 12),
        PrimaryButton(
          label: t('support_feedback_send'),
          busy: _busy,
          onPressed: _rating > 0 ? _send : null,
        ),
      ],
    );
  }
}
