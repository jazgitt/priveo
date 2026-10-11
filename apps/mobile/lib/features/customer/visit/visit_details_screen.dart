import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../cust_strings.dart';
import '../cust_ui.dart';
import '../data/customer_reads_repository.dart';

/// Opens the details of a visit over the current screen (SVC-09).
void openVisitDetails(BuildContext context, String visitId) {
  Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => VisitDetailsScreen(visitId: visitId),
    ),
  );
}

/// Service details with proof (SVC-01, SVC-04, SVC-05, SVC-06). The crew
/// member card, checklist and rating come with the crew and support slices.
class VisitDetailsScreen extends ConsumerWidget {
  const VisitDetailsScreen({super.key, required this.visitId});

  final String visitId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return CustPage(
      title: CustStrings.visitTitle,
      body: AsyncBody<VisitDetailDto>(
        value: ref.watch(visitDetailProvider(visitId)),
        onRetry: () => ref.invalidate(visitDetailProvider(visitId)),
        builder: (v) {
          final photos = [
            for (final p in v.proof)
              if (!p.isVideo) p,
          ];
          final videos = [
            for (final p in v.proof)
              if (p.isVideo) p,
          ];
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(formatDate(v.date), style: text.headlineSmall),
                  ),
                  StatusChip(v.status, tone: statusTone(v.status)),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                [
                  v.vehicleModel,
                  v.vehicleRegistration,
                ].where((s) => s.isNotEmpty).join('  '),
                style: text.bodyMedium?.copyWith(color: b.mute),
              ),
              const SizedBox(height: 20),
              SectionLabel(CustStrings.jobsHeading),
              const SizedBox(height: 8),
              for (final j in v.jobs)
                SectionCard(
                  child: Row(
                    children: [
                      Expanded(child: Text(j.service, style: text.titleSmall)),
                      StatusChip(j.status, tone: statusTone(j.status)),
                    ],
                  ),
                ),
              const SizedBox(height: 20),
              SectionLabel(CustStrings.photosHeading),
              const SizedBox(height: 8),
              if (photos.isEmpty && videos.isEmpty)
                Text(
                  CustStrings.noProofYet,
                  style: text.bodyMedium?.copyWith(color: b.mute),
                ),
              if (photos.isNotEmpty)
                GridView.count(
                  crossAxisCount: 3,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 8,
                  crossAxisSpacing: 8,
                  children: [
                    for (final (i, p) in photos.indexed)
                      InkWell(
                        onTap: () => _viewPhotos(context, photos, i),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: _Photo(p.url, fit: BoxFit.cover),
                        ),
                      ),
                  ],
                ),
              if (videos.isNotEmpty) ...[
                const SizedBox(height: 20),
                SectionLabel(CustStrings.videosHeading),
                const SizedBox(height: 8),
                for (final p in videos)
                  Card(
                    child: ListTile(
                      leading: const Icon(Symbols.play_circle_rounded),
                      title: const Text(CustStrings.playVideo),
                      onTap: () => launchUrl(
                        Uri.parse(p.url),
                        mode: LaunchMode.externalApplication,
                      ),
                    ),
                  ),
              ],
            ],
          );
        },
      ),
    );
  }

  void _viewPhotos(BuildContext context, List<ProofDto> photos, int index) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) =>
            PhotoViewer(urls: [for (final p in photos) p.url], initial: index),
      ),
    );
  }
}

class _Photo extends StatelessWidget {
  const _Photo(this.url, {required this.fit});

  final String url;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) => Image.network(
    url,
    fit: fit,
    errorBuilder: (context, error, stack) => Container(
      color: context.brand.line,
      alignment: Alignment.center,
      child: Icon(Symbols.image_rounded, color: context.brand.mute),
    ),
  );
}

/// Full-screen photos with a position counter and a close button (SVC-05).
class PhotoViewer extends StatefulWidget {
  const PhotoViewer({super.key, required this.urls, this.initial = 0});

  final List<String> urls;
  final int initial;

  @override
  State<PhotoViewer> createState() => _PhotoViewerState();
}

class _PhotoViewerState extends State<PhotoViewer> {
  late final _controller = PageController(initialPage: widget.initial);
  late int _index = widget.initial;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.black,
    body: SafeArea(
      child: Stack(
        children: [
          PageView.builder(
            controller: _controller,
            itemCount: widget.urls.length,
            onPageChanged: (i) => setState(() => _index = i),
            itemBuilder: (_, i) => InteractiveViewer(
              child: _Photo(widget.urls[i], fit: BoxFit.contain),
            ),
          ),
          Positioned(
            top: 8,
            left: 16,
            child: Text(
              CustStrings.photoPosition(_index + 1, widget.urls.length),
              style: const TextStyle(color: Colors.white),
            ),
          ),
          Positioned(
            top: 0,
            right: 4,
            child: IconButton(
              tooltip: CustStrings.close,
              color: Colors.white,
              icon: const Icon(Symbols.close_rounded),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),
        ],
      ),
    ),
  );
}
