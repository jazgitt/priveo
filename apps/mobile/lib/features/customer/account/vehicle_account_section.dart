import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../data/customer_reads_repository.dart';
import '../home/customer_home_data.dart';
import 'account_data.dart';
import 'account_strings.dart';
import 'photo_widgets.dart';

const _basements = ['B1', 'B2', 'B3', 'B4']; // ONB-13

/// What a customer can change on a vehicle (VEH-01, VEH-04) and its RC status
/// (VEH-03): the photo with "Change photo", parking, and the RC document.
class VehicleAccountSection extends ConsumerWidget {
  const VehicleAccountSection({super.key, required this.vehicle});

  final VehicleDetailDto vehicle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SectionLabel(AccountStrings.vehiclePhoto),
              const SizedBox(height: 10),
              VehiclePhotoField(vehicleId: vehicle.id),
            ],
          ),
        ),
        const SizedBox(height: 12),
        SectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      AccountStrings.rcDocument,
                      style: text.bodyMedium?.copyWith(color: b.mute),
                    ),
                  ),
                  StatusChip(
                    vehicle.rcStatus == 'Uploaded'
                        ? AccountStrings.rcUploaded
                        : AccountStrings.rcNotUploaded,
                    tone: vehicle.rcStatus == 'Uploaded'
                        ? ChipTone.ok
                        : ChipTone.neutral,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  onPressed: () => showEditParkingSheet(context, ref, vehicle),
                  child: const Text(AccountStrings.editParking),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Edit the parking basement and number (VEH-04).
Future<void> showEditParkingSheet(
  BuildContext context,
  WidgetRef ref,
  VehicleDetailDto vehicle,
) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  showDragHandle: true,
  builder: (_) => _EditParking(vehicle),
);

class _EditParking extends ConsumerStatefulWidget {
  const _EditParking(this.vehicle);

  final VehicleDetailDto vehicle;

  @override
  ConsumerState<_EditParking> createState() => _EditParkingState();
}

class _EditParkingState extends ConsumerState<_EditParking> {
  late String? _basement = _basements.contains(widget.vehicle.parkingBasement)
      ? widget.vehicle.parkingBasement
      : null;
  late final _number = TextEditingController(
    text: widget.vehicle.parkingNumber,
  );
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _number.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_basement == null) {
      setState(() => _error = AccountStrings.selectBasement);
      return;
    }
    if (!RegExp(r'^\d{1,5}$').hasMatch(_number.text.trim())) {
      setState(() => _error = AccountStrings.enterParking);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      await ref
          .read(accountRepositoryProvider)
          .editParking(
            widget.vehicle.id,
            basement: _basement,
            number: _number.text.trim(),
          );
      ref.invalidate(vehicleDetailProvider(widget.vehicle.id));
      ref.invalidate(vehiclesProvider);
      ref.invalidate(customerHomeProvider);
      messenger.showSnackBar(
        const SnackBar(content: Text(AccountStrings.parkingSaved)),
      );
      navigator.pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e is ApiFailure && e.message != null
              ? e.message
              : AccountStrings.uploadFailed;
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        4,
        20,
        20 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(AccountStrings.editParking, style: text.titleMedium),
          const SizedBox(height: 12),
          Text(AccountStrings.basement, style: text.labelMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final b in _basements)
                ChoiceChip(
                  label: Text(b),
                  selected: _basement == b,
                  onSelected: _busy ? null : (_) => setState(() => _basement = b),
                ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _number,
            enabled: !_busy,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(5),
            ],
            decoration: const InputDecoration(
              labelText: AccountStrings.parkingNumber,
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                _error!,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Theme.of(context).colorScheme.error,
                ),
              ),
            ),
          const SizedBox(height: 16),
          PrimaryButton(
            label: AccountStrings.save,
            busy: _busy,
            onPressed: _save,
          ),
        ],
      ),
    );
  }
}
