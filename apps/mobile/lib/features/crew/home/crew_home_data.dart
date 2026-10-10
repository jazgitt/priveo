import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api.g.dart';
import '../../../core/providers.dart';

final crewHomeProvider = FutureProvider.autoDispose<CrewHome>(
    (ref) => ref.watch(apiProvider).crewHome());
