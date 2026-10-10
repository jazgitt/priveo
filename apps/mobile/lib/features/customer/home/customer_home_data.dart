import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api.g.dart';
import '../../../core/providers.dart';

final customerHomeProvider = FutureProvider.autoDispose<CustomerHome>(
    (ref) => ref.watch(apiProvider).customerHome());

/// Which of the customer's vehicles is selected, by its ID. It is chosen on
/// Home and carries over to the other customer screens (HOME-07).
class SelectedVehicle extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String id) => state = id;
}

final selectedVehicleProvider =
    NotifierProvider<SelectedVehicle, String?>(SelectedVehicle.new);

/// The position of the selected vehicle in [vehicles]. The first one when
/// nothing is selected yet or the selected vehicle is no longer there.
int selectedIndex(List<VehicleCard> vehicles, String? selectedId) {
  final i = vehicles.indexWhere((v) => v.id == selectedId);
  return i < 0 ? 0 : i;
}
