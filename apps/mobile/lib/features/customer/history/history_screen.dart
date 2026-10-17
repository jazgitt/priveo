import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/read_refresh.dart';
import '../../../core/providers.dart';
import 'package:intl/intl.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../cust_strings.dart';
import '../cust_ui.dart';
import '../data/customer_reads_repository.dart';
import '../data/proof_reads_repository.dart';
import '../home/customer_home_data.dart';
import '../home/vehicle_header.dart';
import '../visit/visit_details_screen.dart';
import 'imported_record_screen.dart';
import '../visit/visit_strings.dart';

/// Opens the service history over the current screen.
void openHistory(BuildContext context) {
  Navigator.of(
    context,
  ).push(MaterialPageRoute<void>(builder: (_) => const HistoryScreen()));
}

/// A page of history is this many visits (the API's default).
const _pageSize = 30;

final importedHistoryProvider = FutureProvider.autoDispose<List<ImportedRecord>>((ref) async {
  ref.watch(readRefreshProvider);
  final response = await ref.watch(dioProvider).get<List<dynamic>>('/v1/customer/history/imported');
  return [
    for (final e in response.data ?? const [])
      ImportedRecord.fromJson((e as Map).cast<String, dynamic>()),
  ];
});

/// One row of the history: a visit from the app, or an imported record.
class _Entry {
  _Entry.visit(HistoryItemDto v) : date = v.date, visit = v, imported = null;
  _Entry.imported(ImportedRecord r) : date = r.date, visit = null, imported = r;

  final DateTime? date;
  final HistoryItemDto? visit;
  final ImportedRecord? imported;
}

String _monthKey(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}';

DateTime _monthStart(String key) {
  final p = key.split('-');
  return DateTime(int.parse(p[0]), int.parse(p[1]));
}

/// Visits that are over, one month at a time, newest first, for the selected
/// vehicle (SVC-09, HIST-01, HIST-02). It starts at the current month.
class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  late String _month = _monthKey(DateTime.now());
  List<HistoryItemDto> _items = const [];
  bool _loading = true;
  bool _more = false;
  Object? _error;
  String? _vehicleId;
  bool _started = false;

  String? _selectedVehicle() {
    final home = ref.read(customerHomeProvider).value;
    if (home == null || home.vehicles.isEmpty) return null;
    return home
        .vehicles[selectedIndex(home.vehicles, ref.read(selectedVehicleProvider))]
        .id;
  }

  Future<void> _load({bool append = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await ref
          .read(proofReadsProvider)
          .historyMonth(
            _month,
            vehicleId: _vehicleId,
            offset: append ? _items.length : 0,
          );
      if (!mounted) return;
      setState(() {
        _items = append ? [..._items, ...page] : page;
        _more = page.length >= _pageSize;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  void _shift(int months) {
    final d = _monthStart(_month);
    _month = _monthKey(DateTime(d.year, d.month + months));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(readRefreshProvider, (_, next) {
      if (next.hasValue && !_loading) _load();
    });
    if (!_started) {
      _started = true;
      _vehicleId = _selectedVehicle();
      Future.microtask(_load);
    }
    final meta = ref.watch(historyMetaProvider(_vehicleId)).value;
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final current = _monthKey(DateTime.now());
    final imported = [
      for (final r in ref.watch(importedHistoryProvider).value ?? const <ImportedRecord>[])
        if (_vehicleId == null || r.vehicleId == null || r.vehicleId == _vehicleId) r,
    ];
    // Paging reaches back to the oldest visit or imported record.
    final months = [
      ?meta?.earliestMonth,
      for (final r in imported)
        if (r.date != null) _monthKey(r.date!),
    ]..sort();
    final earliest = months.isEmpty ? null : months.first;
    final canGoBack = earliest == null || _month.compareTo(earliest) > 0;
    final canGoForward = _month.compareTo(current) < 0;
    final label = DateFormat('MMMM yyyy').format(_monthStart(_month));
    return CustPage(
      title: CustStrings.historyTitle,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
            child: VehicleHeader(_vehicleId),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: Row(
              children: [
                IconButton(
                  tooltip: CustStrings.previousMonth,
                  onPressed: canGoBack ? () => _shift(-1) : null,
                  icon: const Icon(Symbols.chevron_left_rounded),
                ),
                Expanded(
                  child: Text(
                    label,
                    textAlign: TextAlign.center,
                    style: text.titleMedium,
                  ),
                ),
                IconButton(
                  tooltip: CustStrings.nextMonth,
                  onPressed: canGoForward ? () => _shift(1) : null,
                  icon: const Icon(Symbols.chevron_right_rounded),
                ),
              ],
            ),
          ),
          Expanded(child: _body(context, text, b, imported, !canGoBack)),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(
              VisitStrings.historyFooter(
                label,
                meta?.memberSince == null
                    ? null
                    : formatDate(meta!.memberSince!),
              ),
              style: text.bodySmall?.copyWith(color: b.mute),
            ),
          ),
        ],
      ),
    );
  }

  Widget _body(BuildContext context, TextTheme text, BrandColors b,
      List<ImportedRecord> imported, bool oldestMonth) {
    if (_loading && _items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _items.isEmpty) {
      return ErrorView(
        message: _error is ApiFailure ? (_error as ApiFailure).message : null,
        onRetry: _load,
      );
    }
    // Visits and imported records of this month in one list, newest first.
    final entries = [
      for (final v in _items) _Entry.visit(v),
      for (final r in imported)
        if (r.date != null && _monthKey(r.date!) == _month) _Entry.imported(r),
    ]..sort((x, y) => y.date!.compareTo(x.date!));
    // Records without a date sit under the oldest month.
    final undated = oldestMonth
        ? [for (final r in imported) if (r.date == null) r]
        : const <ImportedRecord>[];
    if (entries.isEmpty && undated.isEmpty) {
      return Center(child: Text(VisitStrings.historyMonthEmpty));
    }
    return RefreshIndicator(
      onRefresh: () => refreshAll(ref),
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(20),
        children: [
          for (final e in entries) ...[
            e.visit != null
                ? _visitCard(context, text, b, e.visit!)
                : _importedCard(context, text, b, e.imported!),
            const SizedBox(height: 8),
          ],
          if (_more)
            TextButton(
              onPressed: _loading ? null : () => _load(append: true),
              child: const Text(VisitStrings.loadMore),
            ),
          if (undated.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 12, 4, 8),
              child: Text(VisitStrings.undatedHeading, style: text.titleSmall),
            ),
            for (final r in undated) ...[
              _importedCard(context, text, b, r),
              const SizedBox(height: 8),
            ],
          ],
        ],
      ),
    );
  }

  Widget _row(TextTheme text, BrandColors b, VoidCallback onTap,
      String title, String subtitle, String? third, Widget chip) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: text.titleSmall),
                    const SizedBox(height: 4),
                    Text(subtitle, style: text.bodySmall?.copyWith(color: b.mute)),
                    if (third != null) ...[
                      const SizedBox(height: 4),
                      Text(third, style: text.bodySmall?.copyWith(color: b.mute)),
                    ],
                  ],
                ),
              ),
              chip,
              Icon(Symbols.chevron_right_rounded, color: b.mute),
            ],
          ),
        ),
      ),
    );
  }

  /// Every visit opens its service details: proof, checklist, and what the
  /// crew recorded when a job was not done.
  Widget _visitCard(BuildContext context, TextTheme text, BrandColors b,
      HistoryItemDto h) {
    final completed = h.status == 'Completed';
    return _row(
      text,
      b,
      () => openVisitDetails(context, h.visitId),
      [
        formatDate(h.date),
        if (h.finishedAt != null) VisitStrings.finishedShort(h.finishedAt!),
      ].join('  ·  '),
      [
        h.services.join(' + '),
        if (h.photoCount > 0) CustStrings.photoCount(h.photoCount),
      ].where((s) => s.isNotEmpty).join('  ·  '),
      completed
          ? (h.rating == null ? VisitStrings.noRating : VisitStrings.stars(h.rating!))
          : null,
      StatusChip(h.status, tone: statusTone(h.status)),
    );
  }

  Widget _importedCard(BuildContext context, TextTheme text, BrandColors b,
      ImportedRecord r) {
    return _row(
      text,
      b,
      () => openImportedRecord(context, r),
      r.date == null ? VisitStrings.dateUnknown : formatDate(r.date!),
      [r.service, if (_vehicleId == null) r.vehicle]
          .where((s) => s.isNotEmpty).join('  ·  '),
      null,
      const StatusChip(VisitStrings.importedTag),
    );
  }
}
