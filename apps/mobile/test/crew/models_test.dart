import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/features/crew/capture/media_capture.dart';
import 'package:priveo/features/crew/data/crew_models.dart';
import 'package:priveo/features/crew/data/crew_repository.dart';

import 'support.dart';

void main() {
  for (final video in [false, true]) {
    test('capture enforces strict ${video ? 'video' : 'photo'} size boundary', () {
      final limit = video ? maxVideoBytes : maxPhotoBytes;
      final mime = video ? 'video/mp4' : 'image/heic';
      expect(checkCapture(video: video, contentType: mime, bytes: limit - 1), isNull);
      expect(checkCapture(video: video, contentType: mime, bytes: limit), isNotNull);
      expect(checkCapture(video: video, contentType: mime, bytes: limit + 1), isNotNull);
    });
  }
  test('a visit list maps the cards and the counts', () {
    final v = CrewVisitList.fromJson({
      'date': '2026-11-07',
      'society': 'Green Meadows',
      'total': 2,
      'done': 1,
      'left': 1,
      'jobs': [
        cardJson(),
        cardJson(id: 'j2', status: 'Completed', registration: ''),
      ],
    });
    expect(v.date, DateTime(2026, 11, 7));
    expect(v.jobs.first.vehicle.title, 'MH12AB1234');
    expect(v.jobs.first.parking, 'B2-14');
    expect(v.jobs.first.startTime, '06:40');
    expect(v.jobs.first.finishBy, '07:00');
    expect(v.jobs.first.isClosed, isFalse);
    // No plate on file: the car's name is shown instead.
    expect(v.jobs.last.vehicle.title, 'Hyundai Creta');
    expect(v.jobs.last.isClosed, isTrue);
  });

  test('a visit list for all jobs has no date', () {
    final v = CrewVisitList.fromJson({
      'date': null,
      'society': '',
      'total': 0,
      'done': 0,
      'left': 0,
      'jobs': <Object>[],
    });
    expect(v.date, isNull);
    expect(v.jobs, isEmpty);
  });

  test('a job detail maps the checklist, the proof and the outcome', () {
    final d = CrewJobDetail.fromJson({
      'job': cardJson(status: 'Could not complete'),
      'checklist': [
        {'id': 'a', 'label': 'Glass', 'checked_at': '2026-11-07T01:30:00+00:00'},
        {'id': 'b', 'label': 'Wheels', 'checked_at': null},
      ],
      'requirements': {
        'photos_required': 2,
        'videos_required': 1,
        'photos_confirmed': 1,
        'videos_confirmed': 0,
        'pending_uploads': 1,
      },
      'uploads': [
        {'id': 'u1', 'kind': 'photo', 'stage': 'Before', 'status': 'confirmed'}
      ],
      'missing': ['1 more photo to upload'],
      'can_complete': false,
      'outcome': {
        'kind': 'could_not_complete',
        'reason_key': 'car_locked',
        'note': 'Locked',
        'at': '2026-11-07T02:00:00+00:00'
      },
      'started_at': null,
      'finished_at': null,
    });
    expect(d.checklist.first.checked, isTrue);
    expect(d.checklistLeft, 1);
    expect(d.requirements.pendingUploads, 1);
    expect(d.uploads.single.stage, 'Before');
    expect(d.outcome!.reasonKey, 'car_locked');
    expect(d.job.isClosed, isTrue);
  });

  test('the profile knows a Manager', () {
    CrewProfileInfo p(String role) => CrewProfileInfo.fromJson({
          'name': 'Ravi',
          'mobile': '9000000002',
          'society': 'Green Meadows',
          'role': role,
          'working_hours': [
            {'day': 'Mon', 'working': true, 'start': '06:00', 'end': '14:00'},
          ],
        }, hasPhoto: true);
    expect(p('Manager').isManager, isTrue);
    expect(p('Trainee').isManager, isFalse);
    expect(p('Member').hasPhoto, isTrue);
    expect(p('Member').workingHours, 'Mon 06:00 - 14:00');
  });

  test('dates are sent as yyyy-mm-dd', () {
    expect(apiDate(DateTime(2026, 11, 7)), '2026-11-07');
    expect(apiDate(DateTime(2026, 1, 15)), '2026-01-15');
  });

  group('capture rules (CRW-SVC-06)', () {
    test('accepts camera formats, including iPhone HEIC', () {
      expect(contentTypeFor('/a/b.JPG', video: false), 'image/jpeg');
      expect(contentTypeFor('/a/b.heic', video: false), 'image/heic');
      expect(contentTypeFor('/a/b.mov', video: true), 'video/quicktime');
      expect(contentTypeFor('/a/b.mp4', video: true), 'video/mp4');
    });

    test('rejects other formats', () {
      expect(contentTypeFor('/a/b.pdf', video: false), isNull);
      expect(contentTypeFor('/a/b.mp4', video: false), isNull);
      expect(contentTypeFor('/a/noext', video: false), isNull);
    });

    test('photos are under 10 MB and videos under 25 MB', () {
      const mb = 1024 * 1024;
      expect(
          checkCapture(video: false, contentType: 'image/jpeg', bytes: 10 * mb - 1),
          isNull);
      expect(
          checkCapture(
              video: false, contentType: 'image/jpeg', bytes: 10 * mb),
          CaptureProblem.tooLarge);
      expect(
          checkCapture(video: true, contentType: 'video/mp4', bytes: 25 * mb - 1),
          isNull);
      expect(
          checkCapture(
              video: true, contentType: 'video/mp4', bytes: 25 * mb),
          CaptureProblem.tooLarge);
      expect(checkCapture(video: false, contentType: null, bytes: 5),
          CaptureProblem.format);
    });
  });
}
