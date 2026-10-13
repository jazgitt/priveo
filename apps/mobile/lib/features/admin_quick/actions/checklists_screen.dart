import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/ui/widgets.dart';
import 'actions_data.dart';

final adminChecklistsProvider = FutureProvider.autoDispose<List<AdminRow>>(
  (ref) => ref.watch(adminActionsRepositoryProvider).list('/v1/admin/directory/checklists'),
);

/// Reference lists are viewed on mobile and edited in the portal.
class AdminChecklistsScreen extends ConsumerWidget {
  const AdminChecklistsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    appBar: AppBar(title: const Text('Cleaning checklists')),
    body: ref.watch(adminChecklistsProvider).when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, _) => ErrorView(onRetry: () => ref.invalidate(adminChecklistsProvider)),
      data: (lists) => ListView(children: [
        const ListTile(subtitle: Text('Edit these lists in the admin portal. Issued jobs retain their checklist.')),
        for (final list in lists) ExpansionTile(title: Text('${list['service']}'), children: [
          for (final item in (list['items'] as List))
            ListTile(title: Text('${item['label']}'),
              subtitle: Text(item['active'] == true ? 'Active' : 'Inactive')),
        ]),
      ]),
    ),
  );
}
