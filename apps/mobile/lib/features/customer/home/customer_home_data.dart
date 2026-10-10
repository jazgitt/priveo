import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api.g.dart';
import '../../../core/providers.dart';

final customerHomeProvider = FutureProvider.autoDispose<CustomerHome>(
    (ref) => ref.watch(apiProvider).customerHome());
