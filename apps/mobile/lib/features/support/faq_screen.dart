import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ui/widgets.dart';
import 'support_strings.dart';
import 'widgets.dart';

/// One question and its answer (SUP-05).
class FaqItem {
  const FaqItem({required this.question, required this.answer});

  final String question;
  final String answer;

  factory FaqItem.fromJson(Map<String, dynamic> j) =>
      FaqItem(question: j['question'] as String, answer: j['answer'] as String);
}

/// Questions bundled with this app release; tests may override the provider.
List<FaqItem> parseFaqMarkdown(String markdown) {
  final items = <FaqItem>[];
  String? question;
  final answer = <String>[];
  void flush() {
    if (question != null) items.add(FaqItem(question: question, answer: answer.join('\n').trim()));
    answer.clear();
  }
  for (final line in markdown.split('\n')) {
    if (line.startsWith('## ')) {
      flush(); question = line.substring(3).trim();
    } else if (question != null) { answer.add(line); }
  }
  flush(); return items;
}

final faqItemsProvider = FutureProvider.autoDispose<List<FaqItem>>((ref) async =>
    parseFaqMarkdown(await rootBundle.loadString('assets/content/faq.md')));

/// A list of questions that expand to show the answer (SUP-05).
class FaqScreen extends ConsumerWidget {
  const FaqScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faq = ref.watch(faqItemsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(t('support_faq'))),
      body: faq.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(context, e),
          onRetry: () => ref.invalidate(faqItemsProvider),
        ),
        data: (items) => items.isEmpty
            ? Center(child: Text(t('support_faq_empty')))
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final i in items)
                    Card(
                      child: ExpansionTile(
                        title: Text(i.question),
                        childrenPadding: const EdgeInsets.fromLTRB(
                          16,
                          0,
                          16,
                          16,
                        ),
                        expandedCrossAxisAlignment: CrossAxisAlignment.start,
                        children: [Text(i.answer)],
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}
