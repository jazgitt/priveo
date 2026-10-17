import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/widgets.dart';
import '../capture/media_capture.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';
import '../data/crew_models.dart';
import '../upload/upload_queue.dart';
import 'could_not_complete_screen.dart';

const _stages = ['Before', 'During', 'After'];

/// Doing the service: tick the checklist, add photos and a video, then mark
/// complete (CRW-SVC-01 to CRW-SVC-12).
class PerformServiceScreen extends ConsumerStatefulWidget {
  const PerformServiceScreen({super.key, required this.jobId});

  final String jobId;

  @override
  ConsumerState<PerformServiceScreen> createState() => _PerformState();
}

class _PerformState extends ConsumerState<PerformServiceScreen> {
  String _stage = 'Before';
  final _ticking = <String>{};
  bool _completing = false;

  String get _id => widget.jobId;

  Future<void> _tick(ChecklistEntry item, bool checked) async {
    setState(() => _ticking.add(item.id));
    try {
      await ref.read(crewRepositoryProvider).setChecked(_id, item.id, checked);
      ref.invalidate(jobDetailProvider(_id));
      await ref.read(jobDetailProvider(_id).future);
    } catch (e) {
      if (mounted) showSnack(context, failureText(e));
    } finally {
      if (mounted) setState(() => _ticking.remove(item.id));
    }
  }

  Future<void> _capture(bool video, bool camera) async {
    final capture = ref.read(mediaCaptureProvider);
    final queue = ref.read(uploadQueueProvider);
    try {
      final file = video
          ? await capture.video(camera: camera)
          : await capture.photo(camera: camera);
      if (file == null) return;
      final problem = file.problem;
      if (problem != null) {
        if (mounted) {
          showSnack(
              context,
              problem == CaptureProblem.format
                  ? CrewText.formatNotAccepted
                  : (video ? CrewText.videoTooLarge : CrewText.photoTooLarge));
        }
        return;
      }
      await queue.enqueue(
        jobId: _id,
        kind: video ? 'video' : 'photo',
        stage: _stage,
        path: file.path,
        contentType: file.contentType!,
        sizeBytes: file.sizeBytes,
      );
      if (mounted) showSnack(context, CrewText.addedToQueue);
    } catch (e) {
      if (mounted) showSnack(context, CrewText.captureFailed);
    }
  }

  Future<void> _complete() async {
    setState(() => _completing = true);
    try {
      await ref.read(crewRepositoryProvider).complete(_id);
      if (!mounted) return;
      showSnack(context, CrewText.jobCompleted);
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        showSnack(context, failureText(e));
        ref.invalidate(jobDetailProvider(_id));
      }
    } finally {
      if (mounted) setState(() => _completing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // When a waiting file is confirmed, the counts on the server change.
    ref.listen(queuedUploadsProvider, (prev, next) {
      final before = prev?.value?.where((q) => q.jobId == _id).length ?? 0;
      final now = next.value?.where((q) => q.jobId == _id).length ?? 0;
      if (now < before) ref.invalidate(jobDetailProvider(_id));
    });
    final detail = ref.watch(jobDetailProvider(_id));
    final waiting = (ref.watch(queuedUploadsProvider).value ?? const [])
        .where((q) => q.jobId == _id)
        .toList();

    return Scaffold(
      appBar: AppBar(title: Text(CrewText.performTitle)),
      body: detail.when(
        skipLoadingOnReload: true,
        skipError: true,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(jobDetailProvider(_id)),
        ),
        data: (d) {
          final closed = d.job.isClosed;
          final ready = d.canComplete && waiting.isEmpty;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(d.job.vehicle.title,
                  style: Theme.of(context).textTheme.headlineSmall),
              Text('${d.job.service} · ${d.job.parking}'),
              const SizedBox(height: 16),
              SectionLabel(CrewText.checklist),
              const SizedBox(height: 8),
              for (final item in d.checklist)
                CheckboxListTile(
                  key: ValueKey('item-${item.id}'),
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  title: Text(item.label),
                  value: item.checked,
                  onChanged: (closed || _ticking.contains(item.id))
                      ? null
                      : (v) => _tick(item, v ?? false),
                ),
              const SizedBox(height: 16),
              SectionLabel(CrewText.proof),
              const SizedBox(height: 8),
              Text(CrewText.photosProgress(d.requirements.photosConfirmed,
                  d.requirements.photosRequired)),
              Text(CrewText.videosProgress(d.requirements.videosConfirmed,
                  d.requirements.videosRequired)),
              if (!closed) ...[
                const SizedBox(height: 12),
                SegmentedButton<String>(
                  segments: [
                    for (final s in _stages)
                      ButtonSegment(value: s, label: Text(CrewText.stage(s))),
                  ],
                  selected: {_stage},
                  onSelectionChanged: (s) => setState(() => _stage = s.first),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _CaptureButton(
                        icon: Symbols.photo_camera_rounded,
                        label: CrewText.takePhoto,
                        onTap: () => _capture(false, true)),
                    _CaptureButton(
                        icon: Symbols.photo_library_rounded,
                        label: CrewText.choosePhoto,
                        onTap: () => _capture(false, false)),
                    _CaptureButton(
                        icon: Symbols.videocam_rounded,
                        label: CrewText.recordVideo,
                        onTap: () => _capture(true, true)),
                    _CaptureButton(
                        icon: Symbols.video_library_rounded,
                        label: CrewText.chooseVideo,
                        onTap: () => _capture(true, false)),
                  ],
                ),
              ],
              if (waiting.isNotEmpty) ...[
                const SizedBox(height: 12),
                _WaitingList(waiting),
              ],
              const SizedBox(height: 24),
              if (!closed) ...[
                if (!ready)
                  _Missing([
                    ...d.missing,
                    if (waiting.isNotEmpty)
                      CrewText.uploadsWaiting(waiting.length),
                  ]),
                const SizedBox(height: 12),
                PrimaryButton(
                  label: CrewText.markComplete,
                  busy: _completing,
                  onPressed: ready ? _complete : null,
                ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () async {
                    final done = await Navigator.of(context).push<bool>(
                        crewRoute(CouldNotCompleteScreen(jobId: _id)));
                    if (done == true && context.mounted) {
                      Navigator.of(context).pop(true);
                    }
                  },
                  child: Text(CrewText.couldNotComplete),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _CaptureButton extends StatelessWidget {
  const _CaptureButton(
      {required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(icon),
        label: Text(label),
      );
}

class _Missing extends StatelessWidget {
  const _Missing(this.items);
  final List<String> items;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(CrewText.beforeComplete,
              style: Theme.of(context).textTheme.labelLarge),
          for (final m in items) Text('• $m'),
        ],
      );
}

class _WaitingList extends ConsumerWidget {
  const _WaitingList(this.items);
  final List<QueuedUpload> items;

  @override
  Widget build(BuildContext context, WidgetRef ref) => SectionCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(CrewText.waitingToSend,
                style: Theme.of(context).textTheme.labelLarge),
            for (final q in items)
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                            '${q.kind == 'video' ? CrewText.video : CrewText.photo}'
                            ' · ${CrewText.stage(q.stage)}'
                            '${q.step == UploadStep.failed ? ' · ${CrewText.sendFailed}' : ''}'),
                        // Why it failed, for example "This file is too large to send."
                        if (q.step == UploadStep.failed && q.lastError != null)
                          Text(q.lastError!,
                              style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  ),
                  if (q.step == UploadStep.failed) ...[
                    TextButton(
                      onPressed: () =>
                          ref.read(uploadQueueProvider).retry(q.id),
                      child: Text(CrewText.retry),
                    ),
                    TextButton(
                      onPressed: () => _confirmRemove(context, ref, q.id),
                      child: Text(CrewText.remove),
                    ),
                  ],
                ],
              ),
          ],
        ),
      );

  Future<void> _confirmRemove(BuildContext context, WidgetRef ref, int id) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(CrewText.removeUploadTitle),
        content: Text(CrewText.removeUploadBody),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(CrewText.cancel)),
          TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text(CrewText.remove)),
        ],
      ),
    );
    if (yes == true) await ref.read(uploadQueueProvider).remove(id);
  }
}
