import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/admin_quick/actions/checklists_screen.dart';

void main() {
  testWidgets('admin mobile displays the five-step list without editing controls', (tester) async {
    await tester.pumpWidget(ProviderScope(overrides: [
      adminChecklistsProvider.overrideWith((ref) async => [
        {'service': 'Deep Spa', 'items': [for (var i = 1; i <= 5; i++) {'label': 'Step $i', 'active': true}]},
      ]),
    ], child: const MaterialApp(home: AdminChecklistsScreen())));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Deep Spa'));
    await tester.pumpAndSettle();
    for (var i = 1; i <= 5; i++) {
      expect(find.text('Step $i'), findsOneWidget);
    }
    expect(find.byType(TextField), findsNothing);
    expect(find.textContaining('Edit these lists in the admin portal'), findsOneWidget);
  });
}
