import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/network/api_failure.dart';
import '../../l10n/app_localizations.dart';
import 'support_strings.dart';

/// Opens a phone or web link. Tests replace it.
typedef LinkOpener = Future<bool> Function(Uri uri);

final linkOpenerProvider = Provider<LinkOpener>(
    (ref) => (uri) => launchUrl(uri, mode: LaunchMode.externalApplication));

/// The words to show for a failed call: the server's message when it sent one.
String failureText(BuildContext context, Object error) {
  final l = AppLocalizations.of(context);
  return error is ApiFailure ? (error.message ?? l.networkError) : l.networkError;
}

/// Five stars. One tap sets the rating (FDBK-04). Tapping the same star again
/// clears it when [allowClear] is set, for check-in categories (CHK-02).
class StarRating extends StatelessWidget {
  const StarRating({
    super.key,
    required this.value,
    required this.onChanged,
    this.allowClear = false,
    this.size = 36,
  });

  final int value;
  final ValueChanged<int> onChanged;
  final bool allowClear;
  final double size;

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var n = 1; n <= 5; n++)
          Semantics(
            button: true,
            selected: n <= value,
            label: t('support_star', {'n': n}),
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: () => onChanged(allowClear && n == value ? 0 : n),
              child: Padding(
                padding: const EdgeInsets.all(4),
                child: ExcludeSemantics(
                  child: Icon(
                    Symbols.star_rounded,
                    fill: n <= value ? 1 : 0,
                    size: size,
                    color: n <= value ? color : Theme.of(context).disabledColor,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// A small error line under a form.
class FormError extends StatelessWidget {
  const FormError(this.message, {super.key});

  final String? message;

  @override
  Widget build(BuildContext context) => message == null
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(message!,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
        );
}
