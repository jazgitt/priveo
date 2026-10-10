import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import 'theme.dart';
import 'tokens.g.dart';

/// The Priveo logo, white with gold. It is only shown on the dark look.
class BrandLogo extends StatelessWidget {
  const BrandLogo({super.key, required this.width});

  final double width;

  @override
  Widget build(BuildContext context) => Image.asset(
    'assets/brand/priveo-logo.png',
    width: width,
    excludeFromSemantics: true,
  );
}

/// A small gold heading in capitals, above a group of content.
class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Text(
    text.toUpperCase(),
    style: Theme.of(context).textTheme.labelMedium?.copyWith(
      color: context.brand.goldText,
      fontWeight: FontWeight.w700,
      letterSpacing: 1.5,
    ),
  );
}

/// Gold primary button, 56 px high.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.busy = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null && !busy;
    return Semantics(
      button: true,
      enabled: enabled,
      label: label,
      child: Opacity(
        opacity: enabled || busy ? 1 : 0.5,
        // The shadow sits outside the Material, which would clip it.
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(SizeTokens.radiusButton),
            boxShadow: [
              BoxShadow(
                color: context.brand.gold.withValues(alpha: 0.22),
                blurRadius: 26,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Material(
            color: Colors.transparent,
            child: Ink(
              height: SizeTokens.buttonHeight,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: ButtonTokens.primaryGradient,
                  stops: [0, 0.55, 1],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                borderRadius: BorderRadius.circular(SizeTokens.radiusButton),
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(SizeTokens.radiusButton),
                onTap: enabled ? onPressed : null,
                child: Center(
                  child: busy
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: ButtonTokens.primaryText,
                          ),
                        )
                      : ExcludeSemantics(
                          child: Text(
                            label,
                            style: Theme.of(context).textTheme.labelLarge
                                ?.copyWith(color: ButtonTokens.primaryText),
                          ),
                        ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

enum ChipTone { ok, warn, info, spa, neutral }

/// A status chip. The text always says the status, so colour is never alone.
class StatusChip extends StatelessWidget {
  const StatusChip(this.label, {super.key, this.tone = ChipTone.neutral});

  final String label;
  final ChipTone tone;

  /// Maps the API's status words to a tone.
  static ChipTone toneFor(String status) => switch (status.toLowerCase()) {
    'done' || 'active' || 'completed' => ChipTone.ok,
    'in progress' || 'scheduled' => ChipTone.info,
    'pending' || 'due' => ChipTone.warn,
    _ => ChipTone.neutral,
  };

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final color = switch (tone) {
      ChipTone.ok => b.ok,
      ChipTone.warn => b.warn,
      ChipTone.info => b.info,
      ChipTone.spa => b.spa,
      ChipTone.neutral => b.mute,
    };
    return Container(
      height: 26,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(13),
      ),
      child: Center(
        widthFactor: 1,
        child: Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
          ),
        ),
      ),
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(padding: padding ?? const EdgeInsets.all(16), child: child),
  );
}

class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.onRetry, this.message});

  final VoidCallback onRetry;
  final String? message;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message ?? l.loadFailed, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: Text(l.tryAgain)),
          ],
        ),
      ),
    );
  }
}

class ComingSoon extends StatelessWidget {
  const ComingSoon({super.key});

  @override
  Widget build(BuildContext context) => Center(
    child: Text(
      AppLocalizations.of(context).comingSoon,
      style: Theme.of(context).textTheme.headlineSmall,
    ),
  );
}
