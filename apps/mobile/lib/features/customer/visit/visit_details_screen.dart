import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/ui/media_image.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../core/util/format.dart';
import '../../support/feedback_sheet.dart';
import '../../support/report_issue_screen.dart';
import '../cust_strings.dart';
import '../cust_ui.dart';
import '../data/customer_reads_repository.dart';
import '../data/proof_reads_repository.dart';
import '../home/customer_home_data.dart';
import '../home/vehicle_header.dart';
import 'visit_strings.dart';
import 'proof_video_screen.dart';

/// Opens the details of a visit over the current screen (SVC-09).
void openVisitDetails(BuildContext context, String visitId) {
  Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => VisitDetailsScreen(visitId: visitId),
    ),
  );
}

/// How many photos the gallery of one job shows before "View all".
const _galleryLimit = 6;

/// Service details with proof (SVC-01 to SVC-08): the finish time, one crew
/// card per job with its checklist and proof, the rating and the report-an-
/// issue entry.
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
          final completed = v.status == 'Completed';
          // The standard heading of the customer screens: the vehicle card.
          // A vehicle no longer on the account still shows its name.
          final known = ref.watch(customerHomeProvider).value?.vehicles
              .any((x) => x.id == v.vehicleId) ?? false;
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              if (known)
                VehicleHeader(v.vehicleId)
              else ...[
                Text(
                  [
                    v.vehicleModel,
                    v.vehicleRegistration,
                  ].where((s) => s.isNotEmpty).join('  '),
                  style: text.titleSmall,
                ),
                const SizedBox(height: 12),
              ],
              Row(
                children: [
                  Expanded(
                    child: Text(formatDate(v.date), style: text.headlineSmall),
                  ),
                  StatusChip(v.shownStatus, tone: statusTone(v.shownStatus)),
                ],
              ),
              if (v.finishedAt != null) ...[
                const SizedBox(height: 4),
                Text(
                  VisitStrings.finishedAt(v.finishedAt!),
                  style: text.bodyMedium?.copyWith(color: b.mute),
                ),
              ],
              if (v.outcomeSummary.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  v.outcomeSummary,
                  key: const ValueKey('visit-outcome-summary'),
                  style: text.bodyMedium,
                ),
              ],
              const SizedBox(height: 20),
              SectionLabel(CustStrings.jobsHeading),
              const SizedBox(height: 8),
              for (final j in v.jobs) _JobCard(job: j, visitId: v.id),
              if (v.proof.isEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  CustStrings.noProofYet,
                  style: text.bodyMedium?.copyWith(color: b.mute),
                ),
              ],
              if (completed) ...[
                const SizedBox(height: 20),
                _RatingCard(visit: v),
              ],
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => ReportIssueScreen(visitId: v.id),
                  ),
                ),
                icon: const Icon(Symbols.report_rounded, size: 18),
                label: const Text(VisitStrings.reportIssue),
              ),
            ],
          );
        },
      ),
    );
  }
}

/// One job: the crew card, the checklist and the job's proof (SVC-02, SVC-03).
class _JobCard extends StatelessWidget {
  const _JobCard({required this.job, required this.visitId});

  final JobDto job;
  final String visitId;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final name = job.crewName;
    final photos = [
      for (final p in job.proof)
        if (!p.isVideo) p,
    ];
    final videos = [
      for (final p in job.proof)
        if (p.isVideo) p,
    ];
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 18,
                child: Text(
                  name == null || name.isEmpty
                      ? '?'
                      : name.characters.first.toUpperCase(),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name ?? VisitStrings.crewPending,
                      style: text.titleSmall,
                    ),
                    Text(
                      VisitStrings.crewSociety(job.crewSociety),
                      style: text.bodySmall?.copyWith(color: b.mute),
                    ),
                  ],
                ),
              ),
              StatusChip(job.status, tone: statusTone(job.status)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            [
              job.service,
              if (job.finishedAt != null)
                VisitStrings.finishedShort(job.finishedAt!),
            ].join(' · '),
            style: text.bodyMedium?.copyWith(color: b.mute),
          ),
          if (job.outcome != null) ...[
            const SizedBox(height: 12),
            _OutcomeBox(outcome: job.outcome!, service: job.service),
          ],
          if (job.checklist.isNotEmpty) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(child: SectionLabel(VisitStrings.checklistHeading)),
                Text(
                  VisitStrings.checklistSummary(
                    job.checklistDone,
                    job.checklist.length,
                  ),
                  style: text.labelMedium,
                ),
              ],
            ),
            const SizedBox(height: 6),
            for (final c in job.checklist)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  children: [
                    Icon(
                      c.checkedAt != null
                          ? Symbols.check_circle_rounded
                          : Symbols.radio_button_unchecked_rounded,
                      size: 18,
                      color: c.checkedAt != null ? b.ok : b.mute,
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text(c.label)),
                    if (c.checkedAt != null)
                      Text(
                        VisitStrings.clock(c.checkedAt!),
                        style: text.bodySmall?.copyWith(color: b.mute),
                      ),
                  ],
                ),
              ),
          ],
          if (photos.isNotEmpty) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(child: SectionLabel(CustStrings.photosHeading)),
                Text(
                  VisitStrings.photosOf(photos.length),
                  style: text.labelMedium,
                ),
              ],
            ),
            const SizedBox(height: 8),
            GridView.count(
              crossAxisCount: 3,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              children: [
                for (final (i, p) in photos.take(_galleryLimit).indexed)
                  InkWell(
                    onTap: () => _viewPhotos(context, photos, i),
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: _Photo(p.url, fit: BoxFit.cover),
                        ),
                        if (p.isAfter)
                          Positioned(
                            left: 6,
                            top: 6,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.black54,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                VisitStrings.afterLabel,
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
            if (photos.length > _galleryLimit)
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => _viewPhotos(context, photos, 0),
                  child: Text(VisitStrings.viewAll(photos.length)),
                ),
              ),
          ],
          if (videos.isNotEmpty) ...[
            const SizedBox(height: 14),
            SectionLabel(CustStrings.videosHeading),
            const SizedBox(height: 4),
            for (final (index, p) in videos.indexed)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Symbols.play_circle_rounded),
                title: Text(VisitStrings.videoTitle(p.stage, p.takenAt)),
                subtitle: const Text(CustStrings.playVideo),
                onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                  builder: (_) => ProofVideoScreen(reference: ProofVideoReference(
                    visitId: visitId, jobId: job.id, proof: p, videoIndex: index)))),
              ),
          ],
        ],
      ),
    );
  }

  void _viewPhotos(BuildContext context, List<ProofDto> photos, int index) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) => PhotoViewer(
          urls: [for (final p in photos) p.url],
          captions: [
            for (final p in photos)
              VisitStrings.caption(p.stage, p.takenAt, job.service),
          ],
          initial: index,
        ),
      ),
    );
  }
}

/// Why a job was not done: the reason, the crew's note and photo, as the crew
/// recorded them (owner decision 17-Oct-26).
class _OutcomeBox extends StatelessWidget {
  const _OutcomeBox({required this.outcome, required this.service});

  final JobOutcomeDto outcome;
  final String service;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final photo = outcome.photoUrl;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: b.warn.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: b.warn.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Symbols.info_rounded, size: 18, color: b.warn),
              const SizedBox(width: 8),
              Text(VisitStrings.outcomeTitle(outcome.kind), style: text.titleSmall),
            ],
          ),
          if (outcome.reason.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(VisitStrings.outcomeReason, style: text.labelMedium?.copyWith(color: b.mute)),
            Text(outcome.reason, style: text.bodyMedium),
          ],
          if (outcome.note.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(VisitStrings.outcomeNote, style: text.labelMedium?.copyWith(color: b.mute)),
            Text(outcome.note, style: text.bodyMedium),
          ],
          if (photo != null) ...[
            const SizedBox(height: 8),
            Text(VisitStrings.outcomePhoto, style: text.labelMedium?.copyWith(color: b.mute)),
            const SizedBox(height: 6),
            InkWell(
              onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                fullscreenDialog: true,
                builder: (_) => PhotoViewer(
                  urls: [photo],
                  captions: ['${VisitStrings.outcomePhoto} · $service'],
                ),
              )),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: SizedBox(
                  width: 120,
                  height: 90,
                  child: _Photo(photo, fit: BoxFit.cover),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// The rating given, or the prompt to give one (SVC-07).
class _RatingCard extends ConsumerWidget {
  const _RatingCard({required this.visit});

  final VisitDetailDto visit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final given = visit.rating;
    return SectionCard(
      child: Row(
        children: [
          Icon(Symbols.star_rounded, color: b.gold, fill: given == null ? 0 : 1),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              given == null
                  ? VisitStrings.rateClean
                  : VisitStrings.yourRating(given),
              style: text.titleSmall,
            ),
          ),
          TextButton(
            onPressed: () async {
              await showVisitRatingSheet(context, visit.id);
              ref.invalidate(visitDetailProvider(visit.id));
              ref.invalidate(selectedTodayCleanProvider);
              ref.invalidate(todayCleansProvider);
            },
            child: Text(
              given == null
                  ? VisitStrings.rateClean
                  : VisitStrings.changeRating,
            ),
          ),
        ],
      ),
    );
  }
}

class _Photo extends StatelessWidget {
  const _Photo(this.url, {required this.fit});

  final String url;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) => MediaImage(
    url,
    fit: fit,
    fallback: Container(
      color: context.brand.line,
      alignment: Alignment.center,
      child: Icon(Symbols.image_rounded, color: context.brand.mute),
    ),
  );
}

/// Full-screen photos with a position counter, a caption and a close button
/// (SVC-05).
class PhotoViewer extends StatefulWidget {
  const PhotoViewer({
    super.key,
    required this.urls,
    this.captions = const [],
    this.initial = 0,
  });

  final List<String> urls;

  /// One caption per photo (stage, time, service). May be empty.
  final List<String> captions;
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
          if (_index < widget.captions.length)
            Positioned(
              left: 16,
              right: 16,
              bottom: 16,
              child: Text(
                widget.captions[_index],
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white),
              ),
            ),
        ],
      ),
    ),
  );
}
