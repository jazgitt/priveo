import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/widgets.dart';
import '../capture/media_capture.dart';
import '../crew_providers.dart';
import '../crew_text.dart';
import '../crew_ui.dart';

/// The crew member's own details (CRW-PRF-01). Only the photo can be
/// changed (CRW-PRF-02, CRW-PRF-03).
class CrewProfileScreen extends ConsumerStatefulWidget {
  const CrewProfileScreen({super.key});

  @override
  ConsumerState<CrewProfileScreen> createState() => _State();
}

class _State extends ConsumerState<CrewProfileScreen> {
  bool _busy = false;

  Future<void> _changePhoto(bool camera) async {
    setState(() => _busy = true);
    try {
      final file = await ref.read(mediaCaptureProvider).photo(camera: camera);
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
            purpose: 'profile',
            kind: 'photo',
            path: file.path,
            contentType: file.contentType!,
            sizeBytes: file.sizeBytes,
          );
      await ref.read(crewRepositoryProvider).setProfilePhoto(id);
      ref.invalidate(crewProfileProvider);
      if (mounted) showSnack(context, CrewText.photoSaved);
    } catch (e) {
      if (mounted) showSnack(context, failureText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(crewProfileProvider);
    final text = Theme.of(context).textTheme;
    Widget row(String label, String value) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(width: 120, child: Text(label, style: text.labelMedium)),
              Expanded(child: Text(value.isEmpty ? '-' : value)),
            ],
          ),
        );
    return Scaffold(
      appBar: AppBar(title: Text(CrewText.profile)),
      body: profile.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: failureText(e),
          onRetry: () => ref.invalidate(crewProfileProvider),
        ),
        data: (p) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Center(
              child: CircleAvatar(
                radius: 40,
                child: Text(
                    p.name.isEmpty ? '?' : p.name.characters.first.toUpperCase(),
                    style: text.headlineMedium),
              ),
            ),
            const SizedBox(height: 8),
            Center(
              child: Text(p.hasPhoto ? CrewText.photoSaved : CrewText.noPhoto),
            ),
            const SizedBox(height: 16),
            SectionCard(
              child: Column(
                children: [
                  row(CrewText.name, p.name),
                  row(CrewText.mobile, p.mobile),
                  row(CrewText.society, p.society),
                  row(CrewText.role, p.role),
                  row(CrewText.workingHours, p.workingHours),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : () => _changePhoto(true),
                    icon: const Icon(Symbols.photo_camera_rounded),
                    label: Text(CrewText.takePhoto),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : () => _changePhoto(false),
                    icon: const Icon(Symbols.photo_library_rounded),
                    label: Text(CrewText.choosePhoto),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
