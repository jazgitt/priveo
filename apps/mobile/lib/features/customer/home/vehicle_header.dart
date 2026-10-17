import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/api/api.g.dart' show VehicleCard;
import '../../../core/ui/theme.dart';
import '../../../core/ui/tokens.g.dart';
import 'customer_home_data.dart';

/// The vehicle selected on Home, or the first one. Null until Home has loaded.
String? selectedVehicleIdOf(WidgetRef ref) {
  final home = ref.watch(customerHomeProvider).value;
  if (home == null || home.vehicles.isEmpty) return null;
  return home.vehicles[selectedIndex(home.vehicles, ref.watch(selectedVehicleProvider))].id;
}

/// The standard header of every quick-action landing screen: which vehicle the
/// action is for, as its name and registration number. It shows nothing until
/// the vehicle is known.
class VehicleHeader extends ConsumerWidget {
  const VehicleHeader(this.vehicleId, {super.key});

  final String? vehicleId;

  static String nameOf(VehicleCard v) =>
      [v.make, v.model, v.variant].whereType<String>().where((s) => s.isNotEmpty).join(' ');

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final home = ref.watch(customerHomeProvider).value;
    final v = home?.vehicles.where((v) => v.id == vehicleId).firstOrNull;
    if (v == null) return const SizedBox.shrink();
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Semantics(
        container: true,
        label: 'Vehicle: ${nameOf(v)} ${v.registration}',
        child: ExcludeSemantics(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: b.gold.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: b.gold.withValues(alpha: 0.35)),
            ),
            child: Row(
              children: [
                Icon(Symbols.directions_car_rounded, size: 20, color: b.gold),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    nameOf(v),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: text.titleSmall,
                  ),
                ),
                if (v.registration.isNotEmpty) ...[
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: DarkTokens.text,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      v.registration,
                      style: text.labelMedium?.copyWith(
                        color: const Color(0xFF111111),
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.6,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
