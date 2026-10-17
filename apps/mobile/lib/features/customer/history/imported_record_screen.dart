import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../cust_ui.dart';
import '../home/customer_home_data.dart';
import '../home/vehicle_header.dart';
import '../visit/visit_strings.dart';

/// One record kept before the Priveo app, as imported (the owner's
/// spreadsheet). It has no crew, checklist or photos, and its completion was
/// not recorded, so the page says so instead of inventing them.
class ImportedRecord {
  const ImportedRecord({
    required this.id,
    required this.service,
    required this.vehicle,
    this.vehicleId,
    this.date,
    this.paymentStatus,
    this.amountRupees,
    this.notes = '',
  });

  final String id;
  final String service;

  /// The registration or model, or "Unmatched vehicle".
  final String vehicle;
  final String? vehicleId;
  final DateTime? date;
  final String? paymentStatus;
  final int? amountRupees;
  final String notes;

  factory ImportedRecord.fromJson(Map<String, dynamic> j) => ImportedRecord(
    id: j['id'] as String,
    service: (j['service'] as String?) ?? '',
    vehicle: (j['vehicle'] as String?) ?? '',
    vehicleId: j['vehicle_id'] as String?,
    date: j['date'] == null ? null : DateTime.parse(j['date'] as String),
    paymentStatus: j['payment_status'] as String?,
    amountRupees: j['amount_rupees'] as int?,
    notes: (j['notes'] as String?) ?? '',
  );
}

void openImportedRecord(BuildContext context, ImportedRecord record) {
  Navigator.of(context).push(MaterialPageRoute<void>(
    builder: (_) => ImportedRecordScreen(record: record),
  ));
}

class ImportedRecordScreen extends ConsumerWidget {
  const ImportedRecordScreen({super.key, required this.record});

  final ImportedRecord record;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final r = record;
    final known = ref.watch(customerHomeProvider).value?.vehicles
        .any((x) => x.id == r.vehicleId) ?? false;
    Widget row(String label, String value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 96,
            child: Text(label, style: text.bodyMedium?.copyWith(color: b.mute)),
          ),
          Expanded(child: Text(value, style: text.bodyMedium)),
        ],
      ),
    );
    return CustPage(
      title: VisitStrings.importedTitle,
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (known)
            VehicleHeader(r.vehicleId)
          else ...[
            Text(r.vehicle, style: text.titleSmall),
            const SizedBox(height: 12),
          ],
          Row(
            children: [
              Expanded(
                child: Text(
                  r.date == null ? VisitStrings.dateUnknown : formatDate(r.date!),
                  style: text.headlineSmall,
                ),
              ),
              const StatusChip(VisitStrings.importedTag),
            ],
          ),
          const SizedBox(height: 6),
          Text(VisitStrings.importedAbout,
              style: text.bodySmall?.copyWith(color: b.mute)),
          const SizedBox(height: 20),
          SectionCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                row(VisitStrings.serviceLabel, r.service),
                row(VisitStrings.dateLabel,
                    r.date == null ? VisitStrings.dateUnknown : formatDate(r.date!)),
                row(VisitStrings.importedTag, VisitStrings.completionNotRecorded),
                row(VisitStrings.paymentLabel, r.paymentStatus ?? VisitStrings.unknown),
                if (r.amountRupees != null)
                  row(VisitStrings.amountLabel, formatRupees(r.amountRupees!)),
                if (r.notes.isNotEmpty) row(VisitStrings.notesLabel, r.notes),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
