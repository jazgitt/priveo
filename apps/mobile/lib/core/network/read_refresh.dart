import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Active read providers refresh every 30 seconds and immediately on resume.
/// Forms retain their local edits; only watched queries issue network reads.
final readRefreshProvider = StreamProvider<int>((ref) {
  final pulse = _ReadPulse();
  ref.onDispose(pulse.dispose);
  return pulse.stream;
});

class _ReadPulse with WidgetsBindingObserver {
  _ReadPulse() {
    WidgetsBinding.instance.addObserver(this);
    _timer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (_active) _controller.add(++_revision);
    });
  }
  final _controller = StreamController<int>();
  late final Timer _timer;
  int _revision = 0;
  bool _active = WidgetsBinding.instance.lifecycleState == null ||
      WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
  Stream<int> get stream => _controller.stream;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _active = state == AppLifecycleState.resumed;
    if (_active) _controller.add(++_revision);
  }

  void dispose() {
    _timer.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _controller.close();
  }
}
