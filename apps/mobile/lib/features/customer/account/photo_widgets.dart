import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/ui/media_image.dart';
import '../../../core/ui/theme.dart';
import '../../crew/capture/media_capture.dart';
import '../../crew/crew_providers.dart' show mediaCaptureProvider;
import '../data/customer_reads_repository.dart';
import '../home/customer_home_data.dart';
import 'account_data.dart';
import 'account_strings.dart';

/// Takes or picks one photo, checks it against rule 17, and sends it. Returns
/// the stored file, or null when the customer backs out. Throws the message
/// to show as a [String] when the photo cannot be used or sent.
Future<UploadedFile?> captureAndUpload(
  BuildContext context,
  WidgetRef ref, {
  required String purpose,
  String? vehicleId,
  VoidCallback? onSending,
}) async {
  final camera = await showModalBottomSheet<bool>(
    context: context,
    showDragHandle: true,
    builder: (sheet) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Symbols.photo_camera_rounded),
            title: const Text(AccountStrings.takePhoto),
            onTap: () => Navigator.of(sheet).pop(true),
          ),
          ListTile(
            leading: const Icon(Symbols.photo_library_rounded),
            title: const Text(AccountStrings.fromGallery),
            onTap: () => Navigator.of(sheet).pop(false),
          ),
        ],
      ),
    ),
  );
  if (camera == null) return null;
  final file = await ref.read(mediaCaptureProvider).photo(camera: camera);
  if (file == null) return null;
  switch (file.problem) {
    case CaptureProblem.format:
      throw AccountStrings.photoFormat;
    case CaptureProblem.tooLarge:
      throw AccountStrings.photoTooLarge;
    case null:
      break;
  }
  onSending?.call();
  try {
    return await ref
        .read(accountRepositoryProvider)
        .upload(purpose: purpose, file: file, vehicleId: vehicleId);
  } on ApiFailure catch (e) {
    throw e.message ?? AccountStrings.uploadFailed;
  }
}

/// The vehicle photo with its Add or Change button (VEH-01, ONB-22). A photo
/// can be replaced but not removed. With [reportDone] it tells the onboarding
/// review whether the vehicle has a photo.
class VehiclePhotoField extends ConsumerStatefulWidget {
  const VehiclePhotoField({
    super.key,
    required this.vehicleId,
    this.reportDone = false,
    this.height = 180,
  });

  final String vehicleId;
  final bool reportDone;
  final double height;

  @override
  ConsumerState<VehiclePhotoField> createState() => _VehiclePhotoFieldState();
}

class _VehiclePhotoFieldState extends ConsumerState<VehiclePhotoField> {
  String? _url;
  bool _sent = false;
  bool _loaded = false;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await ref
          .read(accountRepositoryProvider)
          .vehicleAccount(widget.vehicleId);
      if (!mounted) return;
      setState(() {
        _url = v.photoUrl;
        _loaded = true;
      });
      _report();
    } catch (_) {
      if (mounted) setState(() => _loaded = true);
    }
  }

  void _report() {
    if (!widget.reportDone) return;
    final has = _url != null || _sent;
    Future.microtask(() {
      if (mounted) {
        ref.read(vehiclePhotoDoneProvider(widget.vehicleId).notifier).state =
            has;
      }
    });
  }

  Future<void> _change() async {
    setState(() => _error = null);
    try {
      final done = await captureAndUpload(
        context,
        ref,
        purpose: 'vehicle',
        vehicleId: widget.vehicleId,
        onSending: () => setState(() => _busy = true),
      );
      if (done == null || !mounted) return;
      setState(() {
        _url = done.url ?? _url;
        _sent = true;
        _busy = false;
      });
      _report();
      ref.invalidate(vehiclesProvider);
      ref.invalidate(accountVehiclesProvider);
      ref.invalidate(vehicleDetailProvider(widget.vehicleId));
      ref.invalidate(customerHomeProvider);
    } on String catch (message) {
      if (mounted) setState(() => _error = message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final has = _url != null || _sent;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Container(
            height: widget.height,
            width: double.infinity,
            color: b.line,
            child: _url != null
                ? MediaImage(_url!, fallback: _placeholder(b))
                : _placeholder(b),
          ),
        ),
        const SizedBox(height: 10),
        if (_busy)
          Row(
            children: [
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(width: 10),
              Text(AccountStrings.uploading, style: text.bodyMedium),
            ],
          )
        else
          OutlinedButton.icon(
            onPressed: !_loaded
                ? null
                : _change,
            icon: const Icon(Symbols.photo_camera_rounded, size: 18),
            label: Text(
              has ? AccountStrings.changePhoto : AccountStrings.addPhoto,
            ),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Semantics(
              liveRegion: true,
              child: Text(
                _error!,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Theme.of(context).colorScheme.error,
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _placeholder(BrandColors b) => Center(
    child: Icon(Symbols.directions_car_rounded, size: 48, color: b.mute),
  );
}

/// A small round thumbnail of a vehicle's photo for the Home card (HOME-02).
/// Nothing shows until the vehicle has one.
class VehiclePhotoThumb extends ConsumerWidget {
  const VehiclePhotoThumb(this.vehicleId, {super.key, this.size = 56});

  final String vehicleId;
  final double size;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final url = ref
        .watch(accountVehiclesProvider)
        .value
        ?.where((v) => v.id == vehicleId)
        .map((v) => v.photoUrl)
        .firstOrNull;
    if (url == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(right: 12),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: SizedBox(
          width: size,
          height: size,
          child: MediaImage(url, fallback: const SizedBox.shrink()),
        ),
      ),
    );
  }
}

/// Complaint photo attachments (ISS-04). The customer can add several. The
/// IDs of the stored photos go to [onChanged].
class ComplaintPhotosField extends ConsumerStatefulWidget {
  const ComplaintPhotosField({super.key, required this.onChanged});

  final ValueChanged<List<String>> onChanged;

  @override
  ConsumerState<ComplaintPhotosField> createState() =>
      _ComplaintPhotosFieldState();
}

class _ComplaintPhotosFieldState extends ConsumerState<ComplaintPhotosField> {
  final _photos = <UploadedFile>[];
  bool _busy = false;
  String? _error;

  static const _max = 10;

  Future<void> _add() async {
    setState(() => _error = null);
    try {
      final done = await captureAndUpload(
        context,
        ref,
        purpose: 'complaint',
        onSending: () => setState(() => _busy = true),
      );
      if (done != null && mounted) {
        setState(() => _photos.add(done));
        widget.onChanged([for (final p in _photos) p.id]);
      }
    } on String catch (message) {
      if (mounted) setState(() => _error = message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _remove(UploadedFile p) {
    setState(() => _photos.remove(p));
    widget.onChanged([for (final p in _photos) p.id]);
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(AccountStrings.attachPhotos, style: text.titleMedium),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final p in _photos)
              Stack(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: SizedBox(
                      width: 72,
                      height: 72,
                      child: p.url == null
                          ? const Icon(Symbols.image_rounded)
                          : MediaImage(p.url!),
                    ),
                  ),
                  Positioned(
                    top: 0,
                    right: 0,
                    child: Semantics(
                      button: true,
                      label: AccountStrings.removePhoto,
                      child: InkWell(
                        onTap: () => _remove(p),
                        child: const Icon(Symbols.cancel_rounded, size: 22),
                      ),
                    ),
                  ),
                ],
              ),
            if (_photos.length < _max)
              OutlinedButton.icon(
                onPressed: _busy ? null : _add,
                icon: _busy
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Symbols.add_a_photo_rounded, size: 18),
                label: const Text(AccountStrings.addComplaintPhoto),
              ),
          ],
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              _error!,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.error,
              ),
            ),
          ),
      ],
    );
  }
}
