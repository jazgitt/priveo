import '../../../core/network/read_refresh.dart';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart' show StateProvider;

import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../changes_money/data/money_models.dart' show SubscriptionDto;
import '../../changes_money/data/money_repository.dart';
import '../../crew/capture/media_capture.dart';
import '../data/customer_reads_repository.dart';

// Hand-written DTOs for the account endpoints (/v1/customer/profile, the
// vehicle edit and the customer uploads). They move to the generated client
// when the contract is regenerated.

/// The customer's profile (ACC-01, ACC-06).
class ProfileDto {
  const ProfileDto({
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.mobile,
    required this.society,
    required this.flat,
    required this.initials,
    this.memberSince,
    this.pendingEmail,
  });

  final String firstName;
  final String lastName;
  final String email;
  final String mobile;
  final String society;
  final String flat;
  final String initials;
  final DateTime? memberSince;

  /// A new email waiting for its code (ACC-08).
  final String? pendingEmail;

  String get fullName => '$firstName $lastName'.trim();

  factory ProfileDto.fromJson(Map<String, dynamic> j) => ProfileDto(
    firstName: j['first_name'] as String,
    lastName: j['last_name'] as String,
    email: j['email'] as String,
    mobile: j['mobile'] as String,
    society: j['society'] as String,
    flat: (j['flat'] as String?) ?? '',
    initials: (j['initials'] as String?) ?? '',
    memberSince: j['member_since'] == null
        ? null
        : DateTime.parse(j['member_since'] as String).toLocal(),
    pendingEmail: j['pending_email'] as String?,
  );
}

/// The vehicle's photo and RC state after an edit or an upload (VEH-01, VEH-03).
class VehicleAccountDto {
  const VehicleAccountDto({
    required this.id,
    required this.parkingBasement,
    required this.parkingNumber,
    required this.photoUrl,
    required this.rcStatus,
  });

  final String id;
  final String parkingBasement;
  final String parkingNumber;
  final String? photoUrl;
  final String rcStatus;

  factory VehicleAccountDto.fromJson(Map<String, dynamic> j) =>
      VehicleAccountDto(
        id: j['id'] as String,
        parkingBasement: j['parking_basement'] as String,
        parkingNumber: j['parking_number'] as String,
        photoUrl: j['photo_url'] as String?,
        rcStatus: j['rc_status'] as String,
      );
}

/// A file the API has stored and confirmed.
class UploadedFile {
  const UploadedFile({required this.id, this.url});

  final String id;
  final String? url;
}

/// The customer's account calls. Failures are thrown as [ApiFailure]. Tests
/// override [accountRepositoryProvider] with a fake.
abstract class AccountRepository {
  Future<ProfileDto> profile();
  Future<ProfileDto> editProfile({
    required String firstName,
    required String lastName,
    required String mobile,
  });

  /// Sends a code to [email]. The old email stays until [verifyEmail].
  Future<void> startEmailChange(String email);
  Future<ProfileDto> verifyEmail(String code);
  Future<void> changePassword({
    required String current,
    required String next,
  });
  Future<VehicleAccountDto> vehicleAccount(String vehicleId);
  Future<VehicleAccountDto> editParking(
    String vehicleId, {
    String? basement,
    String? number,
  });

  /// Asks for a signed URL, sends [file] to it and confirms (VEH-01, ISS-04).
  /// [purpose] is `vehicle`, `complaint` or `rc`.
  Future<UploadedFile> upload({
    required String purpose,
    required CapturedFile file,
    String? vehicleId,
  });
}

class DioAccountRepository implements AccountRepository {
  DioAccountRepository(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> _json(
    Future<Response<dynamic>> Function() run,
  ) async {
    try {
      final r = await run();
      return (r.data as Map).cast<String, dynamic>();
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<ProfileDto> profile() async =>
      ProfileDto.fromJson(await _json(() => _dio.get('/v1/customer/profile')));

  @override
  Future<ProfileDto> editProfile({
    required String firstName,
    required String lastName,
    required String mobile,
  }) async => ProfileDto.fromJson(
    await _json(
      () => _dio.patch(
        '/v1/customer/profile',
        data: {'first_name': firstName, 'last_name': lastName, 'mobile': mobile},
      ),
    ),
  );

  @override
  Future<void> startEmailChange(String email) async {
    await _json(
      () => _dio.post('/v1/customer/profile/email', data: {'email': email}),
    );
  }

  @override
  Future<ProfileDto> verifyEmail(String code) async => ProfileDto.fromJson(
    await _json(
      () => _dio.post('/v1/customer/profile/email/verify', data: {'code': code}),
    ),
  );

  @override
  Future<void> changePassword({
    required String current,
    required String next,
  }) async {
    try {
      await _dio.post<void>(
        '/v1/customer/password',
        data: {'current_password': current, 'new_password': next},
      );
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }

  @override
  Future<VehicleAccountDto> vehicleAccount(String vehicleId) async =>
      VehicleAccountDto.fromJson(
        await _json(() => _dio.get('/v1/customer/vehicles/$vehicleId/account')),
      );

  @override
  Future<VehicleAccountDto> editParking(
    String vehicleId, {
    String? basement,
    String? number,
  }) async => VehicleAccountDto.fromJson(
    await _json(
      () => _dio.patch(
        '/v1/customer/vehicles/$vehicleId',
        data: {'parking_basement': ?basement, 'parking_number': ?number},
      ),
    ),
  );

  @override
  Future<UploadedFile> upload({
    required String purpose,
    required CapturedFile file,
    String? vehicleId,
  }) async {
    try {
      final ticket = (await _dio.post<Map<String, dynamic>>(
        '/v1/customer/uploads',
        data: {
          'purpose': purpose,
          'vehicle_id': ?vehicleId,
          'content_type': file.contentType,
          'size_bytes': file.sizeBytes,
        },
      )).data!;
      final source = File(file.path);
      final length = await source.length();
      await _dio.request<void>(
        ticket['upload_url'] as String,
        data: source.openRead(),
        options: Options(
          method: (ticket['method'] as String?) ?? 'PUT',
          headers: {
            ...((ticket['headers'] as Map?) ?? const {}).cast<String, String>(),
            Headers.contentLengthHeader: length,
          },
          // A signed URL is its own credential. Our token must not go to it.
          extra: {'noAuth': true},
          sendTimeout: const Duration(minutes: 5),
        ),
      );
      final done = (await _dio.post<Map<String, dynamic>>(
        '/v1/customer/uploads/${ticket['id']}/confirm',
      )).data!;
      return UploadedFile(id: done['id'] as String, url: done['url'] as String?);
    } on DioException catch (e) {
      throw ApiFailure.fromDio(e);
    }
  }
}

final accountRepositoryProvider = Provider<AccountRepository>(
  (ref) => DioAccountRepository((ref.watch(readRefreshProvider), ref.watch(dioProvider)).$2),
);

final profileProvider = FutureProvider.autoDispose<ProfileDto>(
  (ref) => ref.watch(accountRepositoryProvider).profile(),
  retry: (_, _) => null,
);

/// The vehicles for the Account cards and the Home photo. A failed look-up is
/// an empty list: those screens work without it, so nothing retries.
final accountVehiclesProvider =
    FutureProvider.autoDispose<List<VehicleSummaryDto>>((ref) async {
      try {
        return await ref.watch(customerReadsProvider).vehicles();
      } catch (_) {
        return const [];
      }
    });

/// A vehicle's subscription for its Account card, or null when it cannot be
/// read (ACC-02).
final accountSubscriptionProvider = FutureProvider.autoDispose
    .family<SubscriptionDto?, String>((ref, vehicleId) async {
      try {
        return await ref.watch(moneyRepositoryProvider).subscription(vehicleId);
      } catch (_) {
        return null;
      }
    });

/// Whether a vehicle has its photo, for the onboarding review (ONB-22). The
/// photo field sets it when it loads and after each upload.
final vehiclePhotoDoneProvider = StateProvider.family<bool, String>(
  (ref, vehicleId) => false,
);
