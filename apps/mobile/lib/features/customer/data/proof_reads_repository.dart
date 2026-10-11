import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../home/customer_home_data.dart';
import 'customer_reads_repository.dart';

/// What the history footer and the month paging need (HIST-02).
class HistoryMetaDto {
  const HistoryMetaDto({
    this.memberSince,
    this.latestMonth,
    this.earliestMonth,
  });

  final DateTime? memberSince;

  /// `yyyy-mm` of the newest and the oldest visit that is over.
  final String? latestMonth;
  final String? earliestMonth;

  factory HistoryMetaDto.fromJson(Map<String, dynamic> j) => HistoryMetaDto(
    memberSince: j['member_since'] == null
        ? null
        : DateTime.parse(j['member_since'] as String),
    latestMonth: j['latest_month'] as String?,
    earliestMonth: j['earliest_month'] as String?,
  );
}

/// A visit completed today, for the Home strip (HOME-03).
class TodayCleanDto {
  const TodayCleanDto({
    required this.vehicleId,
    required this.visitId,
    required this.finishedAt,
    required this.checksDone,
    required this.checksTotal,
    required this.photoCount,
    this.rating,
  });

  final String vehicleId;
  final String visitId;
  final DateTime? finishedAt;
  final int checksDone;
  final int checksTotal;
  final int photoCount;
  final int? rating;

  factory TodayCleanDto.fromJson(Map<String, dynamic> j) => TodayCleanDto(
    vehicleId: j['vehicle_id'] as String,
    visitId: j['visit_id'] as String,
    finishedAt: j['finished_at'] == null
        ? null
        : DateTime.parse(j['finished_at'] as String).toLocal(),
    checksDone: j['checks_done'] as int,
    checksTotal: j['checks_total'] as int,
    photoCount: j['photo_count'] as int,
    rating: j['rating'] as int?,
  );
}

/// The reads that arrived with proof: one month of history, the history
/// footer and today's finished cleans. Kept apart from
/// [CustomerReadsRepository] so existing fakes of that class keep working.
abstract class ProofReadsRepository {
  Future<List<HistoryItemDto>> historyMonth(
    String month, {
    String? vehicleId,
    int offset = 0,
  });
  Future<HistoryMetaDto> historyMeta({String? vehicleId});
  Future<List<TodayCleanDto>> today();
}

class DioProofReadsRepository implements ProofReadsRepository {
  DioProofReadsRepository(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() f) async {
    try {
      return await f();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<List<HistoryItemDto>> historyMonth(
    String month, {
    String? vehicleId,
    int offset = 0,
  }) => _call(() async {
    final r = await _dio.get<List<dynamic>>(
      '/v1/customer/history',
      queryParameters: {
        'month': month,
        'offset': offset,
        'vehicle_id': ?vehicleId,
      },
    );
    return [
      for (final e in r.data!)
        HistoryItemDto.fromJson(e as Map<String, dynamic>),
    ];
  });

  @override
  Future<HistoryMetaDto> historyMeta({String? vehicleId}) => _call(() async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/customer/history/meta',
      queryParameters: {'vehicle_id': ?vehicleId},
    );
    return HistoryMetaDto.fromJson(r.data!);
  });

  @override
  Future<List<TodayCleanDto>> today() => _call(() async {
    final r = await _dio.get<List<dynamic>>('/v1/customer/today');
    return [
      for (final e in r.data!)
        TodayCleanDto.fromJson(e as Map<String, dynamic>),
    ];
  });
}

final proofReadsProvider = Provider<ProofReadsRepository>(
  (ref) => DioProofReadsRepository(ref.watch(dioProvider)),
);

/// The history key: vehicle (null for all) and month (`yyyy-mm`).
typedef HistoryMonthKey = ({String? vehicleId, String month});

final historyMonthProvider = FutureProvider.autoDispose
    .family<List<HistoryItemDto>, HistoryMonthKey>(
      (ref, k) => ref
          .watch(proofReadsProvider)
          .historyMonth(k.month, vehicleId: k.vehicleId),
    );

final historyMetaProvider = FutureProvider.autoDispose
    .family<HistoryMetaDto, String?>(
      (ref, vehicleId) =>
          ref.watch(proofReadsProvider).historyMeta(vehicleId: vehicleId),
    );

/// A failed look-up is an empty list: Home keeps working without the strip.
final todayCleansProvider = FutureProvider.autoDispose<List<TodayCleanDto>>((
  ref,
) async {
  try {
    return await ref.watch(proofReadsProvider).today();
  } catch (_) {
    return const [];
  }
});

/// The selected vehicle's finished clean today, if there is one.
final selectedTodayCleanProvider = Provider.autoDispose<TodayCleanDto?>((ref) {
  final cleans = ref.watch(todayCleansProvider).value ?? const [];
  final home = ref.watch(customerHomeProvider).value;
  if (cleans.isEmpty) return null;
  if (home == null || home.vehicles.isEmpty) return cleans.first;
  final id = home
      .vehicles[selectedIndex(home.vehicles, ref.watch(selectedVehicleProvider))]
      .id;
  for (final c in cleans) {
    if (c.vehicleId == id) return c;
  }
  return null;
});
