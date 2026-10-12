import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/ui/media_image.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../support/widgets.dart' show failureText;
import '../routes_paths.dart';
import 'actions_data.dart';

String _day(Object? text) =>
    text == null ? '—' : formatDate(DateTime.parse('$text'));

class AdminResults<T> extends StatelessWidget {
  const AdminResults({
    super.key,
    required this.future,
    required this.retry,
    required this.builder,
  });
  final Future<T> future;
  final VoidCallback retry;
  final Widget Function(T) builder;
  @override
  Widget build(BuildContext context) => FutureBuilder<T>(
    future: future,
    builder: (context, value) {
      if (value.hasError) {
        return ErrorView(
          message: failureText(context, value.error!),
          onRetry: retry,
        );
      }
      if (!value.hasData) {
        return const Center(child: CircularProgressIndicator());
      }
      return builder(value.data as T);
    },
  );
}

Future<DateTime?> _pickDate(BuildContext context, DateTime initial) =>
    showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );

class AdminCustomersScreen extends ConsumerStatefulWidget {
  const AdminCustomersScreen({super.key});
  @override
  ConsumerState<AdminCustomersScreen> createState() => _AdminCustomersState();
}

class _AdminCustomersState extends ConsumerState<AdminCustomersScreen> {
  String search = '';
  late Future<List<AdminRow>> rows = load();
  Future<List<AdminRow>> load() => ref
      .read(adminActionsRepositoryProvider)
      .list('/v1/admin/customers', {'q': search});
  void refresh() => setState(() {
    rows = load();
  });
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.adminCustomers)),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              decoration: InputDecoration(labelText: l.adminCustomerSearch),
              onChanged: (text) {
                search = text;
                refresh();
              },
            ),
          ),
          Expanded(
            child: AdminResults(
              future: rows,
              retry: refresh,
              builder: (items) => ListView(
                children: [
                  if (items.isEmpty) ListTile(title: Text(l.adminNoCustomers)),
                  for (final c in items)
                    ListTile(
                      title: Text('${c['name']}'),
                      subtitle: Text('${c['email']} · ${c['mobile']}'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () =>
                          context.push(AdminQuickPaths.customer('${c['id']}')),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class AdminCustomerScreen extends ConsumerStatefulWidget {
  const AdminCustomerScreen({super.key, required this.id});
  final String id;
  @override
  ConsumerState<AdminCustomerScreen> createState() => _AdminCustomerState();
}

class _AdminCustomerState extends ConsumerState<AdminCustomerScreen> {
  late Future<AdminRow> row = load();
  Future<AdminRow> load() => ref
      .read(adminActionsRepositoryProvider)
      .detail('/v1/admin/customers/${widget.id}');
  void refresh() => setState(() {
    row = load();
  });
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.adminCustomerDetails)),
      body: AdminResults(
        future: row,
        retry: refresh,
        builder: (c) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              '${c['first_name']} ${c['last_name']}',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            Text('${c['email']} · ${c['mobile']} · ${c['flat']}'),
            Text(
              '${l.adminEmailVerified}: ${c['email_verified'] == true ? l.adminYes : l.adminNo}',
            ),
            for (final v in c['vehicles'] as List)
              _VehicleActions(
                key: ValueKey(v['id']),
                vehicle: Map<String, dynamic>.from(v as Map),
              ),
          ],
        ),
      ),
    );
  }
}

class _VehicleActions extends ConsumerStatefulWidget {
  const _VehicleActions({super.key, required this.vehicle});
  final AdminRow vehicle;
  @override
  ConsumerState<_VehicleActions> createState() => _VehicleActionsState();
}

class _VehicleActionsState extends ConsumerState<_VehicleActions> {
  DateTime start = DateTime.now().add(const Duration(days: 1));
  DateTime end = DateTime.now().add(const Duration(days: 1));
  bool busy = false;
  late Future<AdminRow> changes = load();
  String get path => '/v1/admin/vehicles/${widget.vehicle['id']}';
  Future<AdminRow> load() =>
      ref.read(adminActionsRepositoryProvider).detail('$path/changes');
  Future<void> act(String endpoint, [AdminRow? body]) async {
    setState(() => busy = true);
    try {
      final repo = ref.read(adminActionsRepositoryProvider);
      if (body == null) {
        await repo.remove(endpoint);
      } else {
        await repo.post(endpoint, body);
      }
      if (mounted) {
        setState(() {
          changes = load();
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(failureText(context, e))));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final v = widget.vehicle;
    final sub = v['subscription'] as Map?;
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${v['registration']} · ${v['make']} ${v['model']}'),
          Text(
            '${v['society']} · ${v['parking_basement']}-${v['parking_number']}',
          ),
          if (sub != null)
            Text(
              '${sub['status']} · ${sub['plan_name']} · ${formatRupees(sub['price_rupees'] as int)}',
            ),
          for (final p in v['payments'] as List)
            Text(
              '${p['status']} · ${formatRupees(p['amount_rupees'] as int)} · ${_day(p['due_date'])}',
            ),
          if (sub != null) ...[
            TextButton(
              onPressed: busy
                  ? null
                  : () async {
                      final d = await _pickDate(context, start);
                      if (d != null) setState(() => start = d);
                    },
              child: Text('${l.adminFromDate}: ${formatDate(start)}'),
            ),
            TextButton(
              onPressed: busy
                  ? null
                  : () async {
                      final d = await _pickDate(context, end);
                      if (d != null) setState(() => end = d);
                    },
              child: Text('${l.adminToDate}: ${formatDate(end)}'),
            ),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton(
                  onPressed: busy
                      ? null
                      : () => act('$path/skips', {'date': adminDate(start)}),
                  child: Text(l.adminSkipDate),
                ),
                OutlinedButton(
                  onPressed: busy || end.isBefore(start)
                      ? null
                      : () => act('$path/pauses', {
                          'from_date': adminDate(start),
                          'to_date': adminDate(end),
                        }),
                  child: Text(l.adminPause),
                ),
              ],
            ),
            AdminResults(
              future: changes,
              retry: () => setState(() {
                changes = load();
              }),
              builder: (data) => Column(
                children: [
                  if (data['renewal_date'] != null)
                    Text('${l.adminRenewal}: ${_day(data['renewal_date'])}'),
                  for (final s in data['skips'] as List)
                    ListTile(
                      title: Text(_day(s['start_date'])),
                      trailing: TextButton(
                        onPressed: busy
                            ? null
                            : () => act('$path/skips/${s['id']}'),
                        child: Text(l.adminUnskip),
                      ),
                    ),
                  for (final p in data['pauses'] as List)
                    ListTile(
                      title: Text(
                        '${_day(p['start_date'])} – ${_day(p['end_date'])}',
                      ),
                      trailing: TextButton(
                        onPressed: busy
                            ? null
                            : () => act('$path/pauses/${p['id']}'),
                        child: Text(l.adminEndPause),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class AdminOperationsScreen extends ConsumerStatefulWidget {
  const AdminOperationsScreen({super.key, this.initialDate});
  final DateTime? initialDate;
  @override
  ConsumerState<AdminOperationsScreen> createState() => _AdminOperationsState();
}

class _AdminOperationsState extends ConsumerState<AdminOperationsScreen> {
  late String queue = widget.initialDate == null ? 'missed' : 'scheduled';
  String society = '', reason = '';
  DateTime? start, end;
  late Future<List<AdminRow>> rows;
  late Future<List<AdminRow>> societies = ref
      .read(adminActionsRepositoryProvider)
      .list('/v1/admin/directory/societies');
  late Future<List<AdminRow>> reasons = ref
      .read(adminActionsRepositoryProvider)
      .list('/v1/admin/operations/reasons');
  @override
  void initState() {
    super.initState();
    start = end = widget.initialDate;
    rows = load();
  }

  Future<List<AdminRow>> load() => ref
      .read(adminActionsRepositoryProvider)
      .list('/v1/admin/operations/jobs', {
        'queue': queue,
        if (society.isNotEmpty) 'society_id': society,
        if (reason.isNotEmpty) 'reason_key': reason,
        if (start != null) 'date_from': adminDate(start!),
        if (end != null) 'date_to': adminDate(end!),
      });
  void refresh() => setState(() {
    rows = load();
    reasons = ref
        .read(adminActionsRepositoryProvider)
        .list('/v1/admin/operations/reasons');
    societies = ref
        .read(adminActionsRepositoryProvider)
        .list('/v1/admin/directory/societies');
  });
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.adminOperations)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<String>(
            initialValue: queue,
            decoration: InputDecoration(labelText: l.adminQueue),
            items: [
              DropdownMenuItem(value: 'missed', child: Text(l.adminMissedJobs)),
              DropdownMenuItem(
                value: 'scheduled',
                child: Text(l.adminScheduledWork),
              ),
              DropdownMenuItem(
                value: 'history',
                child: Text(l.adminOutcomeHistory),
              ),
            ],
            onChanged: (v) {
              queue = v!;
              refresh();
            },
          ),
          AdminResults(
            future: societies,
            retry: refresh,
            builder: (items) => DropdownButtonFormField<String>(
              initialValue: society,
              decoration: InputDecoration(labelText: l.adminSocietyFilter),
              items: [
                DropdownMenuItem(value: '', child: Text(l.adminAllSocieties)),
                for (final s in items)
                  DropdownMenuItem(
                    value: '${s['id']}',
                    child: Text('${s['name']}'),
                  ),
              ],
              onChanged: (v) {
                society = v!;
                refresh();
              },
            ),
          ),
          AdminResults(
            future: reasons,
            retry: refresh,
            builder: (items) => DropdownButtonFormField<String>(
              initialValue: reason,
              decoration: InputDecoration(labelText: l.adminFailureReason),
              items: [
                DropdownMenuItem(value: '', child: Text(l.adminAllReasons)),
                for (final r in items)
                  DropdownMenuItem(
                    value: '${r['key']}',
                    child: Text('${r['label']}'),
                  ),
              ],
              onChanged: (v) {
                reason = v!;
                refresh();
              },
            ),
          ),
          Wrap(
            children: [
              TextButton(
                onPressed: () async {
                  final d = await _pickDate(context, start ?? DateTime.now());
                  if (d != null) {
                    start = d;
                    refresh();
                  }
                },
                child: Text(
                  '${l.adminFromDate}: ${start == null ? '—' : formatDate(start!)}',
                ),
              ),
              TextButton(
                onPressed: () async {
                  final d = await _pickDate(context, end ?? DateTime.now());
                  if (d != null) {
                    end = d;
                    refresh();
                  }
                },
                child: Text(
                  '${l.adminToDate}: ${end == null ? '—' : formatDate(end!)}',
                ),
              ),
              TextButton(
                onPressed: () {
                  start = end = null;
                  refresh();
                },
                child: Text(l.adminClearDates),
              ),
            ],
          ),
          AdminResults(
            future: rows,
            retry: refresh,
            builder: (items) => Column(
              children: [
                if (items.isEmpty) Text(l.adminNoJobs),
                for (final job in items)
                  _OperationCard(
                    key: ValueKey('${job['id']}:${job['resolved_at']}'),
                    job: job,
                    reasons: reasons,
                    onSaved: refresh,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _OperationCard extends ConsumerStatefulWidget {
  const _OperationCard({
    super.key,
    required this.job,
    required this.reasons,
    required this.onSaved,
  });
  final AdminRow job;
  final Future<List<AdminRow>> reasons;
  final VoidCallback onSaved;
  @override
  ConsumerState<_OperationCard> createState() => _OperationCardState();
}

class _OperationCardState extends ConsumerState<_OperationCard> {
  String reason = '', note = '';
  bool busy = false;
  Future<void> act(String action) async {
    setState(() => busy = true);
    try {
      await ref.read(adminActionsRepositoryProvider).post(
        action == 'Visit'
            ? '/v1/admin/operations/visits/${widget.job['visit_id']}/skip'
            : '/v1/admin/operations/jobs/${widget.job['id']}/resolve',
        {
          if (action != 'Visit') 'action': action,
          'reason': reason,
          'note': note,
        },
      );
      widget.onSaved();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(failureText(context, e))));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final j = widget.job;
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${j['service']} · ${j['registration']}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text('${j['customer_name']} · ${j['society']} · ${_day(j['date'])}'),
          Text(
            '${j['status'] == 'Could not complete' ? l.adminMissed : j['status']} · ${j['crew_name'] ?? l.adminUnassigned}',
          ),
          Text('${j['reason'] ?? ''} ${j['note'] ?? ''}'),
          if (j['photo_url'] != null)
            SizedBox(height: 180, child: MediaImage(j['photo_url'] as String)),
          if (j['covered_on'] != null)
            Text('${l.adminCoveredOn}: ${_day(j['covered_on'])}'),
          if (j['rescheduled_on'] != null)
            Text(
              '${l.adminRescheduledOn}: ${_day(j['rescheduled_on'])} · ${j['replacement_assigned'] == true ? l.adminAssigned : l.adminNeedsAssignment}',
            ),
          if (j['resolved_at'] != null)
            Text(
              '${j['outcome']} · ${j['resolution_reason']} ${j['resolution_note']} · ${j['resolved_by']} · ${_day(j['resolved_at'])}',
            ),
          if (j['resolved_at'] == null &&
              ['Scheduled', 'Could not complete'].contains(j['status'])) ...[
            AdminResults(
              future: widget.reasons,
              retry: widget.onSaved,
              builder: (items) => DropdownButtonFormField<String>(
                initialValue: reason,
                decoration: InputDecoration(labelText: l.adminOperationsReason),
                items: [
                  DropdownMenuItem(
                    value: '',
                    child: Text(l.adminOptionalReason),
                  ),
                  for (final r in items)
                    DropdownMenuItem(
                      value: '${r['label']}',
                      child: Text('${r['label']}'),
                    ),
                ],
                onChanged: busy ? null : (v) => reason = v!,
              ),
            ),
            TextField(
              maxLength: 2000,
              decoration: InputDecoration(labelText: l.adminOutcomeNote),
              onChanged: (v) => note = v,
            ),
            Text(
              j['service'] == 'Cleaning-External'
                  ? l.adminExteriorExtension
                  : j['service'] == 'Deep Spa'
                  ? l.adminSpaSkip
                  : l.adminInteriorSkip,
            ),
            OutlinedButton(
              onPressed: busy ? null : () => act('Skip'),
              child: Text(l.adminSkipJob),
            ),
            if (j['status'] == 'Could not complete' &&
                j['service'] != 'Cleaning-External')
              OutlinedButton(
                onPressed: busy ? null : () => act('Reschedule'),
                child: Text(l.adminRetryNextDay),
              ),
            if (j['status'] == 'Scheduled')
              OutlinedButton(
                onPressed: busy ? null : () => act('Visit'),
                child: Text(l.adminSkipVisit),
              ),
          ],
        ],
      ),
    );
  }
}

class AdminCrewScreen extends ConsumerStatefulWidget {
  const AdminCrewScreen({super.key});
  @override
  ConsumerState<AdminCrewScreen> createState() => _AdminCrewState();
}

class _AdminCrewState extends ConsumerState<AdminCrewScreen> {
  late Future<List<AdminRow>> rows = load();
  Future<List<AdminRow>> load() =>
      ref.read(adminActionsRepositoryProvider).list('/v1/admin/crew');
  void refresh() => setState(() {
    rows = load();
  });
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.adminCrew)),
      body: AdminResults(
        future: rows,
        retry: refresh,
        builder: (items) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (items.isEmpty) Text(l.adminNoCrew),
            for (final c in items)
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${c['name']} · ${c['role']}'),
                    Text('${c['society']} · ${c['mobile']}'),
                    for (final e in c['exceptions'] as List)
                      Text('${_day(e['date'])} · ${e['kind']} ${e['start']}'),
                    if (c['active'] == true)
                      OutlinedButton(
                        onPressed: () async {
                          await showDialog<void>(
                            context: context,
                            builder: (_) =>
                                _ExceptionDialog(crewId: '${c['id']}'),
                          );
                          if (mounted) refresh();
                        },
                        child: Text(l.adminAddException),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ExceptionDialog extends ConsumerStatefulWidget {
  const _ExceptionDialog({required this.crewId});
  final String crewId;
  @override
  ConsumerState<_ExceptionDialog> createState() => _ExceptionState();
}

class _ExceptionState extends ConsumerState<_ExceptionDialog> {
  DateTime start = DateTime.now(), end = DateTime.now();
  TimeOfDay time = const TimeOfDay(hour: 8, minute: 0);
  String kind = 'Sick';
  bool busy = false;
  Object? error;
  Future<void> save() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await ref.read(adminActionsRepositoryProvider).post(
        '/v1/admin/crew/${widget.crewId}/exceptions',
        {
          'kind': kind,
          'from_date': adminDate(start),
          'to_date': adminDate(end),
          if (kind == 'Late start')
            'start':
                '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}',
        },
      );
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) setState(() => error = e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.adminAddException),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              initialValue: kind,
              decoration: InputDecoration(labelText: l.adminExceptionType),
              items: [
                DropdownMenuItem(value: 'Sick', child: Text(l.adminSick)),
                DropdownMenuItem(value: 'Leave', child: Text(l.adminLeave)),
                DropdownMenuItem(
                  value: 'Late start',
                  child: Text(l.adminLateStart),
                ),
              ],
              onChanged: busy ? null : (v) => setState(() => kind = v!),
            ),
            TextButton(
              onPressed: busy
                  ? null
                  : () async {
                      final d = await _pickDate(context, start);
                      if (d != null) setState(() => start = d);
                    },
              child: Text('${l.adminFromDate}: ${formatDate(start)}'),
            ),
            TextButton(
              onPressed: busy
                  ? null
                  : () async {
                      final d = await _pickDate(context, end);
                      if (d != null) setState(() => end = d);
                    },
              child: Text('${l.adminToDate}: ${formatDate(end)}'),
            ),
            if (kind == 'Late start')
              TextButton(
                onPressed: busy
                    ? null
                    : () async {
                        final t = await showTimePicker(
                          context: context,
                          initialTime: time,
                        );
                        if (t != null) setState(() => time = t);
                      },
                child: Text('${l.adminStartTime}: ${time.format(context)}'),
              ),
            if (error != null) Text(failureText(context, error!)),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: busy ? null : () => Navigator.pop(context),
          child: Text(l.cancel),
        ),
        TextButton(
          onPressed: busy || adminDate(end).compareTo(adminDate(start)) < 0
              ? null
              : save,
          child: Text(l.adminSave),
        ),
      ],
    );
  }
}

class AdminAddonsScreen extends ConsumerStatefulWidget {
  const AdminAddonsScreen({super.key});
  @override
  ConsumerState<AdminAddonsScreen> createState() => _AdminAddonsState();
}

class _AdminAddonsState extends ConsumerState<AdminAddonsScreen> {
  String status = '';
  late Future<List<AdminRow>> rows = load();
  Future<List<AdminRow>> load() => ref
      .read(adminActionsRepositoryProvider)
      .list('/v1/admin/addons', {if (status.isNotEmpty) 'status': status});
  void refresh() => setState(() {
    rows = load();
  });
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.adminAddonRequests)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<String>(
            initialValue: status,
            decoration: InputDecoration(labelText: l.adminStatusFilter),
            items: [
              DropdownMenuItem(value: '', child: Text(l.adminAllStatuses)),
              for (final s in [
                'Requested',
                'Scheduled',
                'Completed',
                'Missed',
                'Cancelled',
              ])
                DropdownMenuItem(value: s, child: Text(s)),
            ],
            onChanged: (v) {
              status = v!;
              refresh();
            },
          ),
          AdminResults(
            future: rows,
            retry: refresh,
            builder: (items) => Column(
              children: [
                if (items.isEmpty) Text(l.adminNoAddons),
                for (final b in items)
                  SectionCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${b['service']} · ${b['vehicle']}'),
                        Text('${b['customer_name']} · ${b['society']}'),
                        Text(
                          '${_day(b['date'])} · ${b['finish_by']} · ${b['status']}',
                        ),
                        Text(
                          '${b['crew_name'] ?? l.adminUnassigned} ${b['start_time'] ?? ''}',
                        ),
                        if (b['standalone'] == true)
                          Text(
                            '${l.adminStandaloneRequest}: ${b['contact_mobile']} ${b['notes']}',
                          )
                        else
                          Text(
                            '${b['payment_status']} · ${formatRupees(b['price_rupees'] as int)}',
                          ),
                        if (b['change_requested'] == true)
                          Text(
                            '${l.adminChangeRequested}: ${_day(b['requested_date'])} · ${b['requested_finish_by']}',
                          ),
                      ],
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

class AdminCheckinsScreen extends ConsumerStatefulWidget {
  const AdminCheckinsScreen({super.key});
  @override
  ConsumerState<AdminCheckinsScreen> createState() => _AdminCheckinsState();
}

class _AdminCheckinsState extends ConsumerState<AdminCheckinsScreen> {
  late Future<AdminRow> report = load();
  Future<AdminRow> load() =>
      ref.read(adminActionsRepositoryProvider).detail('/v1/admin/checkins');
  void refresh() => setState(() {
    report = load();
  });
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.adminCheckins)),
      body: AdminResults(
        future: report,
        retry: refresh,
        builder: (data) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final e in (data['category_averages'] as Map).entries)
              Text('${e.key} · ${e.value}'),
            if ((data['items'] as List).isEmpty) Text(l.adminNoCheckins),
            for (final c in data['items'] as List)
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${c['customer_name']} · ${c['society']}'),
                    Text('${c['vehicle_label']} · ${_day(c['cycle_start'])}'),
                    for (final a in c['answers'] as List)
                      Text('${a['category']} · ${a['rating']}'),
                    Text('${c['comment']}'),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
