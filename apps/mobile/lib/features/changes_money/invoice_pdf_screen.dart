import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pdfx/pdfx.dart';
import '../../core/ui/widgets.dart';
import '../../l10n/app_localizations.dart';
import 'data/invoice_pdf_repository.dart';
import 'money_widgets.dart' show failureText;

typedef InvoicePdfViewerBuilder = Widget Function(Uint8List bytes, VoidCallback retry);

/// Isolates the native renderer so widget tests can exercise loading/retry without a device.
final invoicePdfViewerProvider = Provider<InvoicePdfViewerBuilder>((ref) =>
  (bytes, retry) => _NativeInvoicePdf(key: ObjectKey(bytes), bytes: bytes, retry: retry));

class InvoicePdfScreen extends ConsumerWidget {
  const InvoicePdfScreen({super.key, required this.paymentId, required this.number});
  final String paymentId;
  final String number;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    void retry() => ref.invalidate(invoicePdfProvider(paymentId));
    return Scaffold(appBar: AppBar(title: Text('${l.invoicePdfTitle} $number')),
      body: ref.watch(invoicePdfProvider(paymentId)).when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(message: failureText(error), onRetry: retry),
        data: (bytes) => ref.watch(invoicePdfViewerProvider)(bytes, retry),
      ));
  }
}

class _NativeInvoicePdf extends StatefulWidget {
  const _NativeInvoicePdf({super.key, required this.bytes, required this.retry});
  final Uint8List bytes;
  final VoidCallback retry;
  @override
  State<_NativeInvoicePdf> createState() => _NativeInvoicePdfState();
}

class _NativeInvoicePdfState extends State<_NativeInvoicePdf> {
  late final controller = PdfController(document: PdfDocument.openData(widget.bytes));
  @override
  void dispose() { controller.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => PdfView(controller: controller,
    builders: PdfViewBuilders<DefaultBuilderOptions>(
      options: const DefaultBuilderOptions(),
      documentLoaderBuilder: (_) => const Center(child: CircularProgressIndicator()),
      pageLoaderBuilder: (_) => const Center(child: CircularProgressIndicator()),
      errorBuilder: (_, error) => ErrorView(
        message: AppLocalizations.of(context).invoicePdfUnavailable, onRetry: widget.retry),
    ));
}
