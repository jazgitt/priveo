import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../core/auth/auth_controller.dart';
import '../../l10n/app_localizations.dart';

class SignOutButton extends ConsumerWidget {
  const SignOutButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => IconButton(
        tooltip: AppLocalizations.of(context).signOut,
        icon: const Icon(Symbols.logout_rounded),
        onPressed: () => ref.read(authControllerProvider.notifier).logout(),
      );
}
