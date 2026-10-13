import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

class InvoicePdfRepository {
  InvoicePdfRepository(this.dio);
  final Dio dio;

  Future<Uint8List> load(String paymentId) async {
    try {
      final response = await dio.get<List<int>>(
        '/v1/customer/payments/${Uri.encodeComponent(paymentId)}/invoice.pdf',
        options: Options(responseType: ResponseType.bytes, followRedirects: false,
          receiveTimeout: const Duration(seconds: 30)),
      );
      final data = response.data ?? const <int>[];
      if (data.length < 5 || ascii.decode(data.take(5).toList(), allowInvalid: true) != '%PDF-') {
        throw const ApiFailure(code: 'invalid_pdf', message: 'The invoice PDF could not be opened.');
      }
      return Uint8List.fromList(data);
    } on DioException catch (e) {
      final bytes = e.response?.data;
      if (bytes is List<int>) {
        try {
          final error = jsonDecode(utf8.decode(bytes));
          if (error is Map && error['message'] is String) {
            throw ApiFailure(code: error['code'] as String? ?? 'http_error',
              message: error['message'] as String, statusCode: e.response?.statusCode);
          }
        } on ApiFailure { rethrow; } catch (_) {
          // A non-JSON error response uses the regular network error message.
        }
      }
      throw ApiFailure.fromDio(e);
    }
  }
}

final invoicePdfRepositoryProvider = Provider((ref) => InvoicePdfRepository(ref.watch(dioProvider)));
final invoicePdfProvider = FutureProvider.autoDispose.family<Uint8List, String>((ref, id) =>
  ref.watch(invoicePdfRepositoryProvider).load(id));
