import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ui/widgets.dart';
import 'data/support_repository.dart';
import 'support_strings.dart';
import 'widgets.dart';

/// The crew's ratings screen. It shows general ratings of visits only: an
/// average and a count. It has no customer names, tags or comments, and a
/// rating is never given to a crew member (CRW-RAT-01).
class CrewRatingsScreen extends ConsumerWidget {
  const CrewRatingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ratings = ref.watch(crewRatingsProvider);
    final theme = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(t('support_crew_ratings_title'))),
      body: ratings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
            message: failureText(context, e),
            onRetry: () => ref.invalidate(crewRatingsProvider)),
        data: (r) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(t('support_crew_ratings_note'), style: theme.bodyMedium),
            const SizedBox(height: 16),
            if (r.count == 0 || r.average == null)
              Text(t('support_crew_ratings_none'))
            else
              SectionCard(
                child: Column(
                  children: [
                    Text(t('support_crew_ratings_average'),
                        style: theme.labelMedium),
                    Text(r.average!.toStringAsFixed(1),
                        style: theme.displaySmall),
                    Text(
                        t('support_crew_ratings_count',
                            {'count': r.count, 'days': r.periodDays}),
                        style: theme.bodySmall),
                    const SizedBox(height: 12),
                    for (var star = 5; star >= 1; star--)
                      _Bar(star: star, count: r.stars[star] ?? 0, total: r.count),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar({required this.star, required this.count, required this.total});

  final int star;
  final int count;
  final int total;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            SizedBox(width: 20, child: Text('$star')),
            Expanded(
              child: LinearProgressIndicator(
                  value: total == 0 ? 0 : count / total),
            ),
            SizedBox(
                width: 36,
                child: Text('$count', textAlign: TextAlign.end)),
          ],
        ),
      );
}
