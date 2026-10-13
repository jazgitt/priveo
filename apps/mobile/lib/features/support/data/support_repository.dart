import '../../../core/network/read_refresh.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import 'support_models.dart';

/// What the support screens need from the server. Tests use a fake.
abstract class SupportRepository {
  Future<SupportContact> contact();
  Future<SupportOptions> options();
  Future<Complaint> createComplaint({
    required String category,
    required String description,
    String? visitId,
    List<String> photoKeys = const [],
  });
  Future<List<Complaint>> complaints();
  Future<Complaint> complaint(String id);
  Future<Complaint> reply(String id, String note);
  Future<void> sendFeedback({
    String? category,
    int? rating,
    String comment = '',
    bool testimonial = false,
  });
  Future<void> rateVisit(
    String visitId, {
    required int rating,
    List<String> tags = const [],
    String comment = '',
    bool testimonial = false,
  });
  Future<List<PendingCheckIn>> pendingCheckIns();
  Future<void> submitCheckIn(
    String subscriptionId,
    Map<String, int> ratings,
    String comment,
  );
}

class ApiSupportRepository implements SupportRepository {
  ApiSupportRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<Response<dynamic>> Function() send,
      T Function(dynamic data) read) async {
    try {
      return read((await send()).data);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  static Map<String, dynamic> _map(dynamic d) => d as Map<String, dynamic>;

  @override
  Future<SupportContact> contact() => _call(
      () => _dio.get<dynamic>('/v1/customer/support/contact'),
      (d) => SupportContact.fromJson(_map(d)));

  @override
  Future<SupportOptions> options() => _call(
      () => _dio.get<dynamic>('/v1/customer/support/options'),
      (d) => SupportOptions.fromJson(_map(d)));

  @override
  Future<Complaint> createComplaint({
    required String category,
    required String description,
    String? visitId,
    List<String> photoKeys = const [],
  }) =>
      _call(
          () => _dio.post<dynamic>('/v1/customer/complaints', data: {
                'category': category,
                'description': description,
                'visit_id': ?visitId,
                'photo_keys': photoKeys,
              }),
          (d) => Complaint.fromJson(_map(d)));

  @override
  Future<List<Complaint>> complaints() =>
      _call(() => _dio.get<dynamic>('/v1/customer/complaints'), (d) => [
            for (final e in (d as List)) Complaint.fromJson(_map(e)),
          ]);

  @override
  Future<Complaint> complaint(String id) => _call(
      () => _dio.get<dynamic>('/v1/customer/complaints/$id'),
      (d) => Complaint.fromJson(_map(d)));

  @override
  Future<Complaint> reply(String id, String note) => _call(
      () => _dio.post<dynamic>('/v1/customer/complaints/$id/messages',
          data: {'note': note}),
      (d) => Complaint.fromJson(_map(d)));

  @override
  Future<void> sendFeedback({
    String? category,
    int? rating,
    String comment = '',
    bool testimonial = false,
  }) =>
      _call(
          () => _dio.post<dynamic>('/v1/customer/feedback', data: {
                'category': ?category,
                'rating': ?rating,
                'comment': comment,
                'testimonial_permission': testimonial,
              }),
          (_) {});

  @override
  Future<void> rateVisit(
    String visitId, {
    required int rating,
    List<String> tags = const [],
    String comment = '',
    bool testimonial = false,
  }) =>
      _call(
          () => _dio.put<dynamic>(
                '/v1/customer/visits/${Uri.encodeComponent(visitId)}/rating',
                data: {
                  'rating': rating,
                  'tags': tags,
                  'comment': comment,
                  'testimonial_permission': testimonial,
                },
              ),
          (_) {});

  @override
  Future<List<PendingCheckIn>> pendingCheckIns() => _call(
          () => _dio.get<dynamic>('/v1/customer/checkins/pending'), (d) => [
            for (final e in (d as List)) PendingCheckIn.fromJson(_map(e)),
          ]);

  @override
  Future<void> submitCheckIn(
      String subscriptionId, Map<String, int> ratings, String comment) {
    return _call(
        () => _dio.post<dynamic>('/v1/customer/checkins', data: {
              'subscription_id': subscriptionId,
              'answers': [
                for (final e in ratings.entries)
                  {'category': e.key, 'rating': e.value},
              ],
              'comment': comment,
            }),
        (_) {});
  }
}

final supportRepositoryProvider = Provider<SupportRepository>(
    (ref) => ApiSupportRepository((ref.watch(readRefreshProvider), ref.watch(dioProvider)).$2));

final supportContactProvider = FutureProvider.autoDispose<SupportContact>(
    (ref) => ref.watch(supportRepositoryProvider).contact());

final supportOptionsProvider = FutureProvider.autoDispose<SupportOptions>(
    (ref) => ref.watch(supportRepositoryProvider).options());

final complaintsProvider = FutureProvider.autoDispose<List<Complaint>>(
    (ref) => ref.watch(supportRepositoryProvider).complaints());

final complaintProvider =
    FutureProvider.autoDispose.family<Complaint, String>(
        (ref, id) => ref.watch(supportRepositoryProvider).complaint(id));

/// Check-ins to give now. The Home card (CHK-08) can watch this.
final pendingCheckInsProvider =
    FutureProvider.autoDispose<List<PendingCheckIn>>(
        (ref) => ref.watch(supportRepositoryProvider).pendingCheckIns());
