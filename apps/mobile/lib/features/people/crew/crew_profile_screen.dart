import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../../l10n/app_localizations.dart';
import '../../common/signout_button.dart';
import '../data/people_repository.dart';
import '../people_strings.dart';

/// The crew member's own profile (CRW-PRF-01). Everything on it is read-only
/// (CRW-PRF-03). The photo (CRW-PRF-02) comes with the media slice.
class CrewProfileScreen extends ConsumerWidget {
  const CrewProfileScreen({super.key});

  static const _s = PeopleStrings.instance;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(crewProfileProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(_s.crewProfileTitle),
        actions: const [SignOutButton()],
      ),
      body: profile.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: e is ApiFailure && e.code == 'no_crew_record'
              ? _s.profileMissing
              : null,
          onRetry: () => ref.invalidate(crewProfileProvider),
        ),
        data: (p) => _Body(p),
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body(this.profile);

  final CrewProfile profile;

  static const _s = PeopleStrings.instance;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final initial = profile.name.trim().isEmpty
        ? '?'
        : profile.name.trim()[0].toUpperCase();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            ExcludeSemantics(
              child: CircleAvatar(
                radius: 32,
                backgroundColor: context.brand.gold.withValues(alpha: 0.2),
                child: Text(initial, style: theme.textTheme.headlineSmall),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(profile.name, style: theme.textTheme.headlineSmall),
                  const SizedBox(height: 4),
                  StatusChip(profile.role),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SectionCard(
          child: Column(
            children: [
              _Row(l.mobileNumber, profile.mobile),
              _Row(l.society, profile.society),
              _Row(_s.role, profile.role),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionLabel(_s.workingHours),
        const SizedBox(height: 8),
        SectionCard(
          child: Column(
            children: [
              for (final d in profile.workingHours)
                _Row(
                  d.day,
                  d.working
                      ? _s.hoursRange(formatClock(d.start), formatClock(d.end))
                      : _s.dayOff,
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          _s.profileNote,
          style: theme.textTheme.bodySmall?.copyWith(color: context.brand.mute),
        ),
      ],
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: TextStyle(color: context.brand.mute)),
            const SizedBox(width: 16),
            Flexible(child: Text(value, textAlign: TextAlign.end)),
          ],
        ),
      );
}
