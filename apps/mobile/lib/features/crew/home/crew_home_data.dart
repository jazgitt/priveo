import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../../core/util/format.dart';

class JobCard {
  const JobCard({
    required this.id,
    required this.time,
    required this.vehicle,
    required this.parking,
    required this.service,
    required this.status,
  });

  final String id;
  final String time;
  final String vehicle;
  final String parking;
  final String service;
  final String status;

  factory JobCard.fromJson(Map<String, dynamic> j) => JobCard(
        id: j['id'] as String,
        time: j['time'] as String,
        vehicle: j['vehicle'] as String,
        parking: j['parking'] as String,
        service: j['service'] as String,
        status: j['status'] as String,
      );
}

class CrewHome {
  const CrewHome({
    required this.date,
    required this.society,
    required this.total,
    required this.done,
    required this.left,
    required this.jobs,
  });

  final DateTime date;
  final String society;
  final int total;
  final int done;
  final int left;
  final List<JobCard> jobs;

  factory CrewHome.fromJson(Map<String, dynamic> j) => CrewHome(
        date: parseApiDate(j['date'] as String),
        society: j['society'] as String,
        total: j['total'] as int,
        done: j['done'] as int,
        left: j['left'] as int,
        jobs: [
          for (final x in j['jobs'] as List)
            JobCard.fromJson(x as Map<String, dynamic>),
        ],
      );
}

abstract class CrewHomeRepository {
  Future<CrewHome> fetch();
}

class ApiCrewHomeRepository implements CrewHomeRepository {
  ApiCrewHomeRepository(this._dio);
  final Dio _dio;

  @override
  Future<CrewHome> fetch() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/v1/crew/home');
      return CrewHome.fromJson(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }
}

final crewHomeRepositoryProvider = Provider<CrewHomeRepository>(
    (ref) => ApiCrewHomeRepository(ref.watch(dioProvider)));

final crewHomeProvider = FutureProvider.autoDispose<CrewHome>(
    (ref) => ref.watch(crewHomeRepositoryProvider).fetch());
