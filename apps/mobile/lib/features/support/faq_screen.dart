import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_failure.dart';
import '../../core/providers.dart';
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

/// The questions in order, from `GET /v1/customer/faq`. Tests override it.
final faqItemsProvider = FutureProvider.autoDispose<List<FaqItem>>((ref) async {
  try {
    final r = await ref.watch(dioProvider).get<dynamic>('/v1/customer/faq');
    final items = (r.data as Map<String, dynamic>)['items'] as List<dynamic>;
    return [for (final i in items) FaqItem.fromJson(i as Map<String, dynamic>)];
  } on DioException catch (e) {
    throw ApiFailure.fromDio(e);
  }
});

/// A list of questions that expand to show the answer (SUP-05).
class FaqScreen extends ConsumerWidget {
  const FaqScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faq = ref.watch(faqItemsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(t('support_faq'))),
      body: faq.when(
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
