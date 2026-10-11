import 'dart:io';

import 'package:image_picker/image_picker.dart';
import 'package:video_compress/video_compress.dart';

/// Rule 17 of the customer file, as CRW-SVC-06 applies it to the crew:
/// photos under 10 MB and videos under 25 MB.
const maxPhotoBytes = 10 * 1024 * 1024;
const maxVideoBytes = 25 * 1024 * 1024;

const _photoTypes = {
  'jpg': 'image/jpeg',
  'jpeg': 'image/jpeg',
  'png': 'image/png',
  'heic': 'image/heic',
  'heif': 'image/heif',
  'webp': 'image/webp',
};
const _videoTypes = {
  'mp4': 'video/mp4',
  'm4v': 'video/x-m4v',
  'mov': 'video/quicktime',
  '3gp': 'video/3gpp',
};

/// The content type for a file name, or null for a format that is not accepted.
String? contentTypeFor(String path, {required bool video}) {
  final dot = path.lastIndexOf('.');
  if (dot < 0) return null;
  final ext = path.substring(dot + 1).toLowerCase();
  return (video ? _videoTypes : _photoTypes)[ext];
}

enum CaptureProblem { format, tooLarge }

/// Why a file cannot be sent, or null when it can.
CaptureProblem? checkCapture(
    {required bool video, required String? contentType, required int bytes}) {
  if (contentType == null) return CaptureProblem.format;
  if (bytes <= 0 || bytes > (video ? maxVideoBytes : maxPhotoBytes)) {
    return CaptureProblem.tooLarge;
  }
  return null;
}

class CapturedFile {
  const CapturedFile({
    required this.path,
    required this.contentType,
    required this.sizeBytes,
    required this.video,
  });

  final String path;
  final String? contentType;
  final int sizeBytes;
  final bool video;

  CaptureProblem? get problem =>
      checkCapture(video: video, contentType: contentType, bytes: sizeBytes);
}

/// The camera and the gallery (CRW-SVC-04). A fake stands in for it in tests.
abstract class MediaCapture {
  /// Null when the crew member backs out.
  Future<CapturedFile?> photo({required bool camera});
  Future<CapturedFile?> video({required bool camera});
}

class DeviceMediaCapture implements MediaCapture {
  DeviceMediaCapture([ImagePicker? picker]) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  @override
  Future<CapturedFile?> photo({required bool camera}) async {
    // The picker scales and re-encodes the photo: the compression for photos.
    final shot = await _picker.pickImage(
      source: camera ? ImageSource.camera : ImageSource.gallery,
      maxWidth: 2048,
      maxHeight: 2048,
      imageQuality: 80,
    );
    if (shot == null) return null;
    return CapturedFile(
      path: shot.path,
      contentType: contentTypeFor(shot.path, video: false),
      sizeBytes: await File(shot.path).length(),
      video: false,
    );
  }

  @override
  Future<CapturedFile?> video({required bool camera}) async {
    final clip = await _picker.pickVideo(
      source: camera ? ImageSource.camera : ImageSource.gallery,
      maxDuration: const Duration(minutes: 2),
    );
    if (clip == null) return null;
    // Compress before sending: a long clip is far over 25 MB otherwise.
    final info = await VideoCompress.compressVideo(
      clip.path,
      quality: VideoQuality.MediumQuality,
      deleteOrigin: false,
      includeAudio: true,
    );
    final file = info?.file;
    final path = file?.path ?? clip.path;
    return CapturedFile(
      path: path,
      contentType: contentTypeFor(path, video: true),
      sizeBytes: await File(path).length(),
      video: true,
    );
  }
}
