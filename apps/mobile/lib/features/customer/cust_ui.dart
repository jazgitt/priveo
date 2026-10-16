import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_failure.dart';
import '../../core/ui/widgets.dart';

/// The chip colour of a visit or job status. Missed is a warning.
ChipTone statusTone(String status) => switch (status.toLowerCase()) {
  'missed' => ChipTone.warn,
  'done' || 'completed' => ChipTone.ok,
  'scheduled' || 'in progress' => ChipTone.info,
  'pending' => ChipTone.warn,
  _ => ChipTone.neutral,
};

/// The body of a screen that loads one value: spinner, error with retry, or
/// the data.
class AsyncBody<T> extends StatelessWidget {
  const AsyncBody({
    super.key,
    required this.value,
    required this.onRetry,
    required this.builder,
  });

  final AsyncValue<T> value;
  final VoidCallback onRetry;
  final Widget Function(T data) builder;

  @override
  Widget build(BuildContext context) => value.when(
    skipLoadingOnReload: true,
    skipError: true,
    loading: () => const Center(child: CircularProgressIndicator()),
    error: (e, _) => ErrorView(
      message: e is ApiFailure ? e.message : null,
      onRetry: onRetry,
    ),
    data: builder,
  );
}

/// A page pushed over the shell, with a back arrow.
class CustPage extends StatelessWidget {
  const CustPage({super.key, required this.title, required this.body, this.actions});

  final String title;
  final Widget body;
  final List<Widget>? actions;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(title), actions: actions),
    body: SafeArea(child: body),
  );
}
