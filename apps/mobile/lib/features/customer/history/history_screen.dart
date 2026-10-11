import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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
import '../visit/visit_details_screen.dart';
import '../visit/visit_strings.dart';

/// Opens the service history over the current screen.
void openHistory(BuildContext context) {
  Navigator.of(
    context,
  ).push(MaterialPageRoute<void>(builder: (_) => const HistoryScreen()));
}

/// A page of history is this many visits (the API's default).
const _pageSize = 30;

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
    if (!_started) {
      _started = true;
      _vehicleId = _selectedVehicle();
      Future.microtask(_load);
    }
    final meta = ref.watch(historyMetaProvider(_vehicleId)).value;
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final current = _monthKey(DateTime.now());
    final earliest = meta?.earliestMonth;
    final canGoBack = earliest == null || _month.compareTo(earliest) > 0;
    final canGoForward = _month.compareTo(current) < 0;
    final label = DateFormat('MMMM yyyy').format(_monthStart(_month));
    return CustPage(
      title: CustStrings.historyTitle,
      body: Column(
        children: [
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
          Expanded(child: _body(context, text, b)),
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

  Widget _body(BuildContext context, TextTheme text, BrandColors b) {
    if (_loading && _items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _items.isEmpty) {
      return ErrorView(
        message: _error is ApiFailure ? (_error as ApiFailure).message : null,
        onRetry: _load,
      );
    }
    if (_items.isEmpty) {
      return Center(child: Text(VisitStrings.historyMonthEmpty));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(20),
      itemCount: _items.length + (_more ? 1 : 0),
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (context, i) {
        if (i == _items.length) {
          return TextButton(
            onPressed: _loading ? null : () => _load(append: true),
            child: const Text(VisitStrings.loadMore),
          );
        }
        final h = _items[i];
        final completed = h.status == 'Completed';
        return Card(
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: completed
                ? () => openVisitDetails(context, h.visitId)
                : null,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          [
                            formatDate(h.date),
                            if (h.finishedAt != null)
                              VisitStrings.finishedShort(h.finishedAt!),
                          ].join('  ·  '),
                          style: text.titleSmall,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          [
                            h.services.join(' + '),
                            if (h.photoCount > 0)
                              CustStrings.photoCount(h.photoCount),
                          ].where((s) => s.isNotEmpty).join('  ·  '),
                          style: text.bodySmall?.copyWith(color: b.mute),
                        ),
                        if (completed) ...[
                          const SizedBox(height: 4),
                          Text(
                            h.rating == null
                                ? VisitStrings.noRating
                                : VisitStrings.stars(h.rating!),
                            style: text.bodySmall?.copyWith(color: b.mute),
                          ),
                        ],
                      ],
                    ),
                  ),
                  StatusChip(h.status, tone: statusTone(h.status)),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
