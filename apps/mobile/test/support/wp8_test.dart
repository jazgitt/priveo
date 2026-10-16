// WP8: the FAQ (SUP-01, SUP-05), the feedback side tab (FDBK-01) and the
// invoice page (SUB-12).
import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/changes_money/data/money_repository.dart';
import 'package:priveo/features/changes_money/invoice_screen.dart';
import 'package:priveo/features/support/data/support_repository.dart';
import 'package:priveo/features/support/faq_screen.dart';
import 'package:priveo/features/support/feedback_tab.dart';
import 'package:priveo/features/support/routes.dart' as support;
import 'package:priveo/features/support/widgets.dart';
import 'package:priveo/l10n/app_localizations.dart';

import '../changes_money/fakes.dart';
import 'support_fakes.dart';

Widget _app(Widget home, List<Override> overrides) => ProviderScope(
  overrides: overrides,
  child: MaterialApp(
    theme: customerTheme,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: home,
  ),
);

void main() {
  testWidgets('Help lists the FAQ and its questions expand (SUP-01, SUP-05)', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 2;
    addTearDown(tester.view.reset);
    final router = GoRouter(
      initialLocation: support.SupportRoutes.help,
      routes: support.routes,
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          supportRepositoryProvider.overrideWithValue(FakeSupportRepository()),
          faqItemsProvider.overrideWith(
            (ref) async => const [
              FaqItem(
                question: 'How does billing work?',
                answer: 'Every 30 days.',
              ),
              FaqItem(question: 'How do I skip?', answer: 'By 9 PM.'),
            ],
          ),
        ],
        child: MaterialApp.router(
          theme: customerTheme,
          routerConfig: router,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Frequently asked questions'));
    await tester.pumpAndSettle();
    expect(find.text('How does billing work?'), findsOneWidget);
    expect(find.text('Every 30 days.'), findsNothing);
    await tester.tap(find.text('How does billing work?'));
    await tester.pumpAndSettle();
    expect(find.text('Every 30 days.'), findsOneWidget);
  });

  testWidgets(
    'the feedback tab opens feedback and moves along the edge (FDBK-01)',
    (tester) async {
      var opened = 0;
      await tester.pumpWidget(
        _app(
          Scaffold(
            body: FeedbackSideTab(
              onOpen: () => opened++,
              child: const SizedBox.expand(),
            ),
          ),
          const [],
        ),
      );
      final tab = find.byIcon(Symbols.feedback_rounded);
      expect(tab, findsOneWidget);
      final before = tester.getCenter(tab);
      await tester.drag(tab, const Offset(0, -120));
      await tester.pump();
      final after = tester.getCenter(tab);
      expect(after.dy, lessThan(before.dy));
      expect(after.dx, before.dx);
      await tester.tap(tab);
      expect(opened, 1);
    },
  );

  testWidgets('the invoice page copies and emails the invoice (SUB-12)', (
    tester,
  ) async {
    final opened = <Uri>[];
    String? copied;
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (call) async {
        if (call.method == 'Clipboard.setData') {
          copied = (call.arguments as Map)['text'] as String;
        }
        return null;
      },
    );
    addTearDown(
      () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        null,
      ),
    );
    await tester.pumpWidget(
      _app(const InvoiceScreen(paymentId: 'p0'), [
        moneyRepositoryProvider.overrideWithValue(FakeMoneyRepository()),
        linkOpenerProvider.overrideWithValue((uri) async {
          opened.add(uri);
          return true;
        }),
      ]),
    );
    await tester.pumpAndSettle();
    expect(find.text('PRV102643210001'), findsOneWidget);
    await tester.tap(find.text('Copy invoice'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Invoice copied.'), findsOneWidget);
    expect(copied, contains('PRV102643210001'));
    await tester.tap(find.text('Email invoice'));
    await tester.pumpAndSettle();
    expect(opened.single.scheme, 'mailto');
    expect(opened.single.queryParameters['body'], contains('PRV102643210001'));
  });
}
