import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api.g.dart';
import '../../../core/providers.dart';

final adminHomeProvider = FutureProvider.autoDispose<AdminHome>(
    (ref) => ref.watch(apiProvider).adminHome());
