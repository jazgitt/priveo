import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';

/// One day of a crew member's working hours (ADM-CRW-04).
class DayHours {
  const DayHours({
    required this.day,
    required this.working,
    this.start = '',
    this.end = '',
  });

  final String day;
  final bool working;

  /// `HH:MM`. Empty on a day off.
  final String start;
  final String end;

  factory DayHours.fromJson(Map<String, dynamic> j) => DayHours(
        day: j['day'] as String,
        working: j['working'] as bool,
        start: (j['start'] as String?) ?? '',
        end: (j['end'] as String?) ?? '',
      );
}

/// What a crew member sees of themselves (CRW-PRF-01). It carries no
/// customer data.
class CrewProfile {
  const CrewProfile({
    required this.name,
    required this.mobile,
    required this.society,
    required this.role,
    required this.workingHours,
  });

  final String name;
  final String mobile;
  final String society;
  final String role;
  final List<DayHours> workingHours;

  factory CrewProfile.fromJson(Map<String, dynamic> j) => CrewProfile(
        name: j['name'] as String,
        mobile: j['mobile'] as String,
        society: j['society'] as String,
        role: j['role'] as String,
        workingHours: [
          for (final h in j['working_hours'] as List<dynamic>)
            DayHours.fromJson(h as Map<String, dynamic>),
        ],
      );
}

abstract class PeopleRepository {
  Future<CrewProfile> crewProfile();
}

/// Calls the API through Dio. The generated client does not have these
/// endpoints yet.
class ApiPeopleRepository implements PeopleRepository {
  ApiPeopleRepository(this._dio);

  final Dio _dio;

  @override
  Future<CrewProfile> crewProfile() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/v1/crew/profile');
      return CrewProfile.fromJson(r.data!);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }
}

final peopleRepositoryProvider = Provider<PeopleRepository>(
    (ref) => ApiPeopleRepository(ref.watch(dioProvider)));

final crewProfileProvider = FutureProvider.autoDispose<CrewProfile>(
    (ref) => ref.watch(peopleRepositoryProvider).crewProfile());
