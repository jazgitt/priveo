import '../../../core/network/read_refresh.dart';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import 'money_models.dart';

/// What the changes and money screens need from the API. Tests use a fake.
abstract class MoneyRepository {
  Future<ChangesDto> changes(String vehicleId);
  Future<List<UpcomingDayDto>> upcoming(String vehicleId);
  Future<ChangeDto> skip(String vehicleId, DateTime date);
  Future<void> unskip(String vehicleId, String skipId);
  Future<ChangeDto> pause(String vehicleId, DateTime from, DateTime to);
  Future<ChangeDto> endPause(String vehicleId, String pauseId);

  Future<SubscriptionDto> subscription(String vehicleId);
  Future<List<PaymentDto>> payments(String vehicleId);
  Future<PaymentDetailDto> paymentDetail(String paymentId);
  Future<PaymentDetailDto> payNext(String vehicleId);
  Future<PaymentDetailDto> markPaid(String paymentId);
  Future<InvoiceDto> invoice(String paymentId);

  Future<AddonsDto> addons();
  Future<AddonRequestDto> requestAddon(
      String vehicleId, DateTime date, String finishBy);
  Future<AddonRequestDto> requestStandalone(
      {String? vehicleId,
      required DateTime date,
      required String finishBy,
      required String mobile,
      required String notes});
  Future<AddonRequestDto> cancelAddon(String addonId);
}

String _ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// A new key for each user action. The API treats a repeat of the same key
/// as the same request, so a retry on a poor network never doubles it.
String newIdempotencyKey() {
  final r = Random.secure();
  return List.generate(16, (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0'))
      .join();
}

class DioMoneyRepository implements MoneyRepository {
  DioMoneyRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<Response<dynamic>> Function() send,
      T Function(dynamic data) read) async {
    try {
      final r = await send();
      return read(r.data);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  Options _key() =>
      Options(headers: {'Idempotency-Key': newIdempotencyKey()});

  Map<String, dynamic> _map(dynamic d) => d as Map<String, dynamic>;

  @override
  Future<ChangesDto> changes(String v) => _call(
      () => _dio.get<dynamic>('/v1/customer/vehicles/$v/changes'),
      (d) => ChangesDto.fromJson(_map(d)));

  @override
  Future<List<UpcomingDayDto>> upcoming(String v) =>
      _call(() => _dio.get<dynamic>('/v1/customer/vehicles/$v/upcoming'), (d) => [
            for (final x in d as List)
              UpcomingDayDto.fromJson(x as Map<String, dynamic>)
          ]);

  @override
  Future<ChangeDto> skip(String v, DateTime date) => _call(
      () => _dio.post<dynamic>('/v1/customer/vehicles/$v/skips',
          data: {'date': _ymd(date)}, options: _key()),
      (d) => ChangeDto.fromJson(_map(d)));

  @override
  Future<void> unskip(String v, String skipId) => _call(
      () => _dio.delete<dynamic>('/v1/customer/vehicles/$v/skips/$skipId'),
      (_) {});

  @override
  Future<ChangeDto> pause(String v, DateTime from, DateTime to) => _call(
      () => _dio.post<dynamic>('/v1/customer/vehicles/$v/pauses',
          data: {'from_date': _ymd(from), 'to_date': _ymd(to)}, options: _key()),
      (d) => ChangeDto.fromJson(_map(d)));

  @override
  Future<ChangeDto> endPause(String v, String pauseId) => _call(
      () => _dio.delete<dynamic>('/v1/customer/vehicles/$v/pauses/$pauseId'),
      (d) => ChangeDto.fromJson(_map(d)));

  @override
  Future<SubscriptionDto> subscription(String v) => _call(
      () => _dio.get<dynamic>('/v1/customer/vehicles/$v/subscription'),
      (d) => SubscriptionDto.fromJson(_map(d)));

  @override
  Future<List<PaymentDto>> payments(String v) =>
      _call(() => _dio.get<dynamic>('/v1/customer/vehicles/$v/payments'), (d) => [
            for (final x in d as List) PaymentDto.fromJson(x as Map<String, dynamic>)
          ]);

  @override
  Future<PaymentDetailDto> paymentDetail(String id) => _call(
      () => _dio.get<dynamic>('/v1/customer/payments/$id'),
      (d) => PaymentDetailDto.fromJson(_map(d)));

  @override
  Future<PaymentDetailDto> payNext(String v) => _call(
      () => _dio.post<dynamic>('/v1/customer/vehicles/$v/payments/next'),
      (d) => PaymentDetailDto.fromJson(_map(d)));

  @override
  Future<PaymentDetailDto> markPaid(String id) => _call(
      () => _dio.post<dynamic>('/v1/customer/payments/$id/paid'),
      (d) => PaymentDetailDto.fromJson(_map(d)));

  @override
  Future<InvoiceDto> invoice(String id) => _call(
      () => _dio.get<dynamic>('/v1/customer/payments/$id/invoice'),
      (d) => InvoiceDto.fromJson(_map(d)));

  @override
  Future<AddonsDto> addons() => _call(
      () => _dio.get<dynamic>('/v1/customer/addons'), (d) => AddonsDto.fromJson(_map(d)));

  @override
  Future<AddonRequestDto> requestAddon(String v, DateTime date, String finishBy) =>
      _call(
          () => _dio.post<dynamic>('/v1/customer/vehicles/$v/addons',
              data: {'service': 'Deep Spa', 'date': _ymd(date), 'finish_by': finishBy},
              options: _key()),
          (d) => AddonRequestDto.fromJson(_map(d)));

  @override
  Future<AddonRequestDto> requestStandalone(
          {String? vehicleId,
          required DateTime date,
          required String finishBy,
          required String mobile,
          required String notes}) =>
      _call(
          () => _dio.post<dynamic>('/v1/customer/addons/standalone',
              data: {
                'service': 'Deep Spa',
                'vehicle_id': vehicleId,
                'date': _ymd(date),
                'finish_by': finishBy,
                'contact_mobile': mobile,
                'notes': notes,
              },
              options: _key()),
          (d) => AddonRequestDto.fromJson(_map(d)));

  @override
  Future<AddonRequestDto> cancelAddon(String id) => _call(
      () => _dio.delete<dynamic>('/v1/customer/addons/$id'),
      (d) => AddonRequestDto.fromJson(_map(d)));
}

final moneyRepositoryProvider = Provider<MoneyRepository>(
    (ref) => DioMoneyRepository((ref.watch(readRefreshProvider), ref.watch(dioProvider)).$2));

final upcomingProvider = FutureProvider.autoDispose
    .family<List<UpcomingDayDto>, String>(
        (ref, vehicleId) => ref.watch(moneyRepositoryProvider).upcoming(vehicleId));

final changesProvider = FutureProvider.autoDispose.family<ChangesDto, String>(
    (ref, vehicleId) => ref.watch(moneyRepositoryProvider).changes(vehicleId));

final subscriptionProvider = FutureProvider.autoDispose
    .family<SubscriptionDto, String>((ref, vehicleId) =>
        ref.watch(moneyRepositoryProvider).subscription(vehicleId));

final billingHistoryProvider = FutureProvider.autoDispose
    .family<List<PaymentDto>, String>(
        (ref, vehicleId) => ref.watch(moneyRepositoryProvider).payments(vehicleId));

final paymentDetailProvider = FutureProvider.autoDispose
    .family<PaymentDetailDto, String>((ref, paymentId) =>
        ref.watch(moneyRepositoryProvider).paymentDetail(paymentId));

/// The subscription as the service calendar needs it (the dates it covers).
/// A failed load gives null, so the calendar shows every day instead of an
/// error or a retry loop.
final calendarSubscriptionProvider = FutureProvider.autoDispose
    .family<SubscriptionDto?, String>((ref, vehicleId) async {
  try {
    return await ref.watch(moneyRepositoryProvider).subscription(vehicleId);
  } catch (_) {
    return null;
  }
});

final addonsProvider = FutureProvider.autoDispose<AddonsDto>(
    (ref) => ref.watch(moneyRepositoryProvider).addons());
