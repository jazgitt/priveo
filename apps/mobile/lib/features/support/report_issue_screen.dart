import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../core/util/format.dart';
import '../customer/account/account_strings.dart';
import '../customer/account/photo_widgets.dart' show ComplaintPhotosField;
import '../customer/data/customer_reads_repository.dart';
import '../customer/home/vehicle_header.dart';
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
  String? _visitId;

  /// Set once the customer picks a linked visit themselves (even "none"), so
  /// the default is not applied over their choice.
  bool _visitChosen = false;
  List<String> _photoKeys = const [];

  @override
  void initState() {
    super.initState();
    _visitId = widget.visitId;
  }

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
            visitId: _visitId,
            photoKeys: _photoKeys,
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
    // The report is about one vehicle: the one the visit belongs to when the
    // customer came from a visit, otherwise the vehicle selected on Home. The
    // linked visit starts as that vehicle's latest visit (ISS-02).
    final visits = ref.watch(_recentVisitsProvider).value ?? const <HistoryItemDto>[];
    final from = widget.visitId == null
        ? null
        : visits.where((v) => v.visitId == widget.visitId).firstOrNull;
    final vehicleId = from?.vehicleId ?? selectedVehicleIdOf(ref);
    final ofVehicle = [
      for (final v in visits)
        if (vehicleId == null || v.vehicleId == vehicleId) v,
    ];
    if (!_visitChosen && _visitId == null && ofVehicle.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && !_visitChosen && _visitId == null) {
          setState(() => _visitId = ofVehicle.first.visitId);
        }
      });
    }
    return Scaffold(
      appBar: AppBar(title: Text(t('support_report_title'))),
      body: options.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(context, e),
            onRetry: () => ref.invalidate(supportOptionsProvider)),
        data: (o) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            VehicleHeader(vehicleId),
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
            const SizedBox(height: 16),
            _VisitSelector(
              selected: _visitId,
              visits: ofVehicle,
              onChanged: (v) => setState(() {
                _visitId = v;
                _visitChosen = true;
              }),
            ), // ISS-02
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
            const SizedBox(height: 16),
            ComplaintPhotosField(
              onChanged: (keys) => _photoKeys = keys,
            ), // ISS-04
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

/// Which visit the report is about (ISS-02). It starts on the visit the
/// customer came from. The list is the customer's recent visits that are over.
class _VisitSelector extends ConsumerWidget {
  const _VisitSelector({
    required this.selected,
    required this.visits,
    required this.onChanged,
  });

  final String? selected;
  final List<HistoryItemDto> visits;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // The visit the customer came from stays on the list even when it is not
    // in the recent ones.
    final ids = {for (final v in visits) v.visitId};
    return DropdownButtonFormField<String?>(
      initialValue: selected,
      isExpanded: true,
      decoration: const InputDecoration(labelText: AccountStrings.linkedVisit),
      items: [
        const DropdownMenuItem<String?>(
          value: null,
          child: Text(AccountStrings.noLinkedVisit),
        ),
        if (selected != null && !ids.contains(selected))
          DropdownMenuItem<String?>(
            value: selected,
            child: Text(t('support_issue_linked_visit')),
          ),
        for (final v in visits)
          DropdownMenuItem<String?>(
            value: v.visitId,
            child: Text(
              '${formatDate(v.date)} · ${v.services.join(', ')}',
              overflow: TextOverflow.ellipsis,
            ),
          ),
      ],
      onChanged: onChanged,
    );
  }
}

final _recentVisitsProvider =
    FutureProvider.autoDispose<List<HistoryItemDto>>((ref) async {
  try {
    return await ref.watch(customerReadsProvider).history();
  } catch (_) {
    return const [];
  }
});
