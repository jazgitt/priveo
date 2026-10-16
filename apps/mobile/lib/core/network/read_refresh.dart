import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Active read providers refresh once when the app returns to the foreground
/// after being away for [awayBeforeRefresh] or more. A shorter absence changes
/// nothing. There is no timer and no polling. Forms retain their local edits; only
/// watched queries issue network reads. Screens keep their data on screen
/// while a refresh runs (see `skipLoadingOnReload` on their `.when` calls).
/// How long the app must be in the background before returning refreshes it.
const awayBeforeRefresh = Duration(minutes: 5);

final readPulseProvider = Provider<ReadPulse>((ref) {
  final pulse = ReadPulse();
  ref.onDispose(pulse.dispose);
  return pulse;
});

final readRefreshProvider =
    StreamProvider<int>((ref) => ref.watch(readPulseProvider).stream);

/// Pull to refresh on any screen: refreshes the data of every open screen at
/// once, not only the one pulled. [read] reads this screen's own data so the
/// pull spinner ends when it has arrived.
Future<void> refreshAll(WidgetRef ref, [Future<Object?> Function()? read]) async {
  ref.read(readPulseProvider).refresh();
  await Future<void>.delayed(Duration.zero); // lets the pulse reach the providers
  if (read != null) await read();
}

class ReadPulse with WidgetsBindingObserver {
  ReadPulse({DateTime Function()? now}) : _now = now ?? DateTime.now {
    WidgetsBinding.instance.addObserver(this);
  }
  final DateTime Function() _now;
  DateTime? _leftAt;
  final _controller = StreamController<int>();
  int _revision = 0;
  bool _active = WidgetsBinding.instance.lifecycleState == null ||
      WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
  Stream<int> get stream => _controller.stream;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _active = state == AppLifecycleState.resumed;
    if (state == AppLifecycleState.paused || state == AppLifecycleState.hidden) {
      _leftAt ??= _now();
    } else if (_active) {
      final left = _leftAt;
      _leftAt = null;
      if (left != null && _now().difference(left) >= awayBeforeRefresh) {
        _controller.add(++_revision);
      }
    }
  }

  /// Tells every watching read to load again.
  void refresh() {
    if (!_controller.isClosed) _controller.add(++_revision);
  }

  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller.close();
  }
}
