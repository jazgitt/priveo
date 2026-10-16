import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/widgets.dart';
import '../capture/media_capture.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';

/// Could not complete (CRW-CNC-01, CRW-CNC-02): a reason from the list is
/// required. A note and a photo are optional. A Manager uses the same screen
/// for another crew member's job (CRW-MGR-02).
class CouldNotCompleteScreen extends ConsumerStatefulWidget {
  const CouldNotCompleteScreen(
      {super.key, required this.jobId, this.manager = false});

  final String jobId;
  final bool manager;

  @override
  ConsumerState<CouldNotCompleteScreen> createState() => _State();
}

class _State extends ConsumerState<CouldNotCompleteScreen> {
  final _note = TextEditingController();
  String? _reason;
  String? _photoId;
  bool _busy = false;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _addPhoto() async {
    setState(() => _busy = true);
    try {
      final file = await ref.read(mediaCaptureProvider).photo(camera: true);
      if (file == null) return;
      final problem = file.problem;
      if (problem != null) {
        if (mounted) {
          showSnack(
              context,
              problem == CaptureProblem.format
                  ? CrewText.formatNotAccepted
                  : CrewText.photoTooLarge);
        }
        return;
      }
      final id = await ref.read(uploadQueueProvider).sendNow(
            purpose: 'reason',
            jobId: widget.jobId,
            kind: 'photo',
            path: file.path,
            contentType: file.contentType!,
            sizeBytes: file.sizeBytes,
          );
      if (mounted) setState(() => _photoId = id);
    } catch (e) {
      if (mounted) showSnack(context, failureText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    final repo = ref.read(crewRepositoryProvider);
    try {
      final note = _note.text.trim();
      if (widget.manager) {
        await repo.managerCouldNotComplete(widget.jobId,
            reasonKey: _reason!, note: note, uploadId: _photoId);
      } else {
        await repo.couldNotComplete(widget.jobId,
            reasonKey: _reason!, note: note, uploadId: _photoId);
      }
      if (!mounted) return;
      showSnack(context, CrewText.markedCouldNotComplete);
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) showSnack(context, failureText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final reasons = ref.watch(reasonsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(CrewText.couldNotComplete)),
      body: reasons.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(reasonsProvider),
        ),
        data: (list) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            SectionLabel(CrewText.reason),
            const SizedBox(height: 8),
            for (final r in list)
              ListTile(
                key: ValueKey('reason-${r.key}'),
                contentPadding: EdgeInsets.zero,
                title: Text(r.label),
                selected: _reason == r.key,
                trailing: _reason == r.key
                    ? const Icon(Symbols.check_circle_rounded)
                    : const Icon(Symbols.circle_rounded),
                onTap: () => setState(() => _reason = r.key),
              ),
            const SizedBox(height: 16),
            TextField(
              controller: _note,
              maxLength: 500,
              maxLines: 3,
              decoration: InputDecoration(labelText: CrewText.noteOptional),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _busy ? null : _addPhoto,
              icon: Icon(_photoId == null
                  ? Symbols.photo_camera_rounded
                  : Symbols.check_circle_rounded),
              label: Text(
                  _photoId == null ? CrewText.addPhoto : CrewText.photoAttached),
            ),
            const SizedBox(height: 24),
            PrimaryButton(
              label: CrewText.confirm,
              busy: _busy,
              onPressed: _reason == null ? null : _submit,
            ),
          ],
        ),
      ),
    );
  }
}
