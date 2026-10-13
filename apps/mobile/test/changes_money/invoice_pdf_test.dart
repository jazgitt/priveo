import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/changes_money/data/invoice_pdf_repository.dart';
import 'package:priveo/features/changes_money/data/money_repository.dart';
import 'package:priveo/features/changes_money/invoice_pdf_screen.dart';
import 'package:priveo/features/changes_money/invoice_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';
import 'fakes.dart';

class PdfAdapter implements HttpClientAdapter {
  final requests = <RequestOptions>[];
  int status = 200;
  String content = '%PDF-1.7 fake document';
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream,
      Future<void>? cancel) async {
    requests.add(options);
    return ResponseBody.fromString(content, status, headers: {
      Headers.contentTypeHeader: [status == 200 ? 'application/pdf' : 'application/json'],
    });
  }
  @override
  void close({bool force = false}) {}
}

class FakePdfRepository extends InvoicePdfRepository {
  FakePdfRepository() : super(Dio());
  int calls = 0;
  bool fail = false;
  @override
  Future<Uint8List> load(String paymentId) async {
    calls++;
    if (fail) throw const ApiFailure(code: 'no_invoice', message: 'The admin has not issued this invoice yet.');
    return Uint8List.fromList(ascii.encode('%PDF-1.7 fake document'));
  }
}

Future<void> app(WidgetTester tester, Widget screen, FakePdfRepository pdf) async {
  await tester.pumpWidget(ProviderScope(overrides: [
    moneyRepositoryProvider.overrideWithValue(FakeMoneyRepository()),
    invoicePdfRepositoryProvider.overrideWithValue(pdf),
    invoicePdfViewerProvider.overrideWithValue((bytes, retry) => const Text('PDF preview')),
  ], child: MaterialApp(theme: customerTheme,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales, home: screen)));
  await tester.pumpAndSettle();
}

void main() {
  test('PDF requests use the authenticated API and preserve binary bytes', () async {
    final adapter = PdfAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example',
      headers: {'Authorization': 'Bearer unit-test-token'}))..httpClientAdapter = adapter;
    final bytes = await InvoicePdfRepository(dio).load('payment1');
    expect(ascii.decode(bytes), adapter.content);
    expect(adapter.requests.single.path, '/v1/customer/payments/payment1/invoice.pdf');
    expect(adapter.requests.single.headers['Authorization'], 'Bearer unit-test-token');
    expect(adapter.requests.single.responseType, ResponseType.bytes);
    expect(adapter.requests.single.followRedirects, isFalse);
  });
  test('non-PDF success responses are rejected instead of passed to the renderer', () async {
    final adapter = PdfAdapter()..content = '<html>gateway error</html>';
    final repo = InvoicePdfRepository(Dio()..httpClientAdapter = adapter);
    await expectLater(repo.load('p1'), throwsA(isA<ApiFailure>().having((e) => e.code, 'code', 'invalid_pdf')));
  });
  test('binary JSON errors retain the backend message and status', () async {
    final adapter = PdfAdapter()..status = 404
      ..content = jsonEncode({'code': 'no_invoice', 'message': 'The admin has not issued this invoice yet.'});
    final repo = InvoicePdfRepository(Dio()..httpClientAdapter = adapter);
    await expectLater(repo.load('p1'), throwsA(isA<ApiFailure>()
      .having((e) => e.code, 'code', 'no_invoice').having((e) => e.statusCode, 'status', 404)));
  });
  testWidgets('invoice summary opens the PDF without adding save/share actions', (tester) async {
    final pdf = FakePdfRepository();
    await app(tester, const InvoiceScreen(paymentId: 'p0'), pdf);
    expect(pdf.calls, 0);
    await tester.ensureVisible(find.text('Open invoice PDF'));
    await tester.tap(find.text('Open invoice PDF')); await tester.pumpAndSettle();
    expect(find.text('PDF preview'), findsOneWidget);
    expect(pdf.calls, 1);
    expect(find.text('Share PDF'), findsNothing);
    expect(find.text('Save PDF'), findsNothing);
  });
  testWidgets('PDF errors offer retry and reload after recovery', (tester) async {
    final pdf = FakePdfRepository()..fail = true;
    await app(tester, const InvoicePdfScreen(paymentId: 'p1', number: 'PRV102600000001'), pdf);
    expect(find.text('The admin has not issued this invoice yet.'), findsOneWidget);
    pdf.fail = false;
    await tester.tap(find.text('Try again')); await tester.pumpAndSettle();
    expect(pdf.calls, 2);
    expect(find.text('PDF preview'), findsOneWidget);
  });
}
