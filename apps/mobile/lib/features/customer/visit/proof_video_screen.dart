import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../../core/ui/media_image.dart';
import '../../../core/ui/widgets.dart';
import '../../../l10n/app_localizations.dart';
import '../data/customer_reads_repository.dart';
import 'visit_strings.dart';

/// One owned proof item, independent of the signed URL's expiry.
class ProofVideoReference {
  const ProofVideoReference({required this.visitId, required this.jobId,
    required this.proof, required this.videoIndex});
  final String visitId;
  final String jobId;
  final ProofDto proof;
  final int videoIndex;

  ProofDto refreshed(VisitDetailDto visit) {
    final jobs = visit.jobs.where((job) => job.id == jobId);
    if (jobs.isEmpty) throw const ApiFailure(code: 'proof_missing');
    final videos = jobs.first.proof.where((item) => item.isVideo).toList();
    if (proof.id != null) {
      final matches = videos.where((item) => item.id == proof.id);
      if (matches.isEmpty) throw const ApiFailure(code: 'proof_missing');
      return matches.first;
    }
    // Older APIs have no item ID. Prefer its timestamp; use its original index only
    // when the legacy item has neither identity nor a capture timestamp.
    if (proof.takenAt != null) {
      final matches = videos.where((item) => item.takenAt == proof.takenAt && item.stage == proof.stage);
      if (matches.length != 1) throw const ApiFailure(code: 'proof_missing');
      return matches.first;
    }
    if (videoIndex < 0 || videoIndex >= videos.length) throw const ApiFailure(code: 'proof_missing');
    return videos[videoIndex];
  }
}

/// The native player is isolated so behavior tests can use a deterministic fake.
abstract class ProofVideoPlayback extends ChangeNotifier {
  VideoPlayerValue get value;
  Future<void> initialize();
  Future<void> play();
  Future<void> pause();
  Future<void> seekTo(Duration position);
  Widget view();
}

class NativeProofVideoPlayback extends ProofVideoPlayback {
  NativeProofVideoPlayback(Uri uri) : controller = VideoPlayerController.networkUrl(uri) {
    // Signed media URLs carry their own credentials. Never send the API bearer token.
    controller.addListener(notifyListeners);
  }
  final VideoPlayerController controller;
  @override
  VideoPlayerValue get value => controller.value;
  @override
  Future<void> initialize() => controller.initialize();
  @override
  Future<void> play() => controller.play();
  @override
  Future<void> pause() => controller.pause();
  @override
  Future<void> seekTo(Duration position) => controller.seekTo(position);
  @override
  Widget view() => VideoPlayer(controller);
  @override
  void dispose() {
    controller.removeListener(notifyListeners);
    unawaited(controller.dispose());
    super.dispose();
  }
}

final proofVideoPlaybackProvider = Provider<ProofVideoPlayback Function(Uri)>(
  (ref) => NativeProofVideoPlayback.new);

class ProofVideoScreen extends ConsumerStatefulWidget {
  const ProofVideoScreen({super.key, required this.reference});
  final ProofVideoReference reference;
  @override
  ConsumerState<ProofVideoScreen> createState() => _ProofVideoState();
}

class _ProofVideoState extends ConsumerState<ProofVideoScreen> with WidgetsBindingObserver {
  ProofVideoPlayback? playback;
  bool loading = true;
  Object? error;
  int generation = 0;
  Timer? initializationTimer;
  Completer<void>? initialization;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(load(refresh: false));
  }

  void changed() {
    if (!mounted) return;
    setState(() {
      if (playback?.value.hasError == true) {
        error = const ApiFailure(code: 'video_unavailable');
        loading = false;
      }
    });
  }

  void releasePlayer() {
    initializationTimer?.cancel();
    initializationTimer = null;
    final pending = initialization;
    initialization = null;
    if (pending != null && !pending.isCompleted) pending.completeError(StateError('Player released'));
    final old = playback;
    playback = null;
    old?.removeListener(changed);
    old?.dispose();
  }

  Future<void> initializePlayer(ProofVideoPlayback player) async {
    final pending = Completer<void>();
    initialization = pending;
    final timer = Timer(const Duration(seconds: 30), () {
      if (!pending.isCompleted) pending.completeError(TimeoutException('Video initialization timed out'));
    });
    initializationTimer = timer;
    unawaited(Future<void>.sync(player.initialize).then((_) {
      if (!pending.isCompleted) pending.complete();
    }, onError: (Object error, StackTrace stack) {
      if (!pending.isCompleted) pending.completeError(error, stack);
    }));
    try { await pending.future; }
    finally {
      timer.cancel();
      if (identical(initialization, pending)) { initialization = null; initializationTimer = null; }
    }
  }

  Future<void> load({required bool refresh}) async {
    final current = ++generation;
    releasePlayer();
    if (mounted) setState(() { loading = true; error = null; });
    try {
      var proof = widget.reference.proof;
      if (refresh) {
        final visit = await ref.read(customerReadsProvider).visit(widget.reference.visitId);
        proof = widget.reference.refreshed(visit);
        ref.invalidate(visitDetailProvider(widget.reference.visitId));
      }
      if (!mounted || current != generation) return;
      final uri = Uri.parse(absoluteMediaUrl(ref.read(dioProvider).options.baseUrl, proof.url));
      if (!['http', 'https'].contains(uri.scheme) || uri.host.isEmpty) {
        throw const ApiFailure(code: 'video_unavailable');
      }
      final player = ref.read(proofVideoPlaybackProvider)(uri);
      playback = player;
      player.addListener(changed);
      await initializePlayer(player);
      if (!mounted || current != generation) return;
      if (player.value.hasError || !player.value.isInitialized) {
        throw const ApiFailure(code: 'video_unavailable');
      }
      setState(() => loading = false);
    } catch (e) {
      if (!mounted || current != generation) return;
      releasePlayer();
      setState(() { loading = false; error = e; });
    }
  }

  Future<void> control(Future<void> Function(ProofVideoPlayback) action) async {
    final player = playback;
    if (player == null) return;
    try { await action(player); }
    catch (e) {
      if (mounted && identical(playback, player)) {
        releasePlayer();
        setState(() => error = e);
      }
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed && playback?.value.isPlaying == true) {
      unawaited(control((player) => player.pause()));
    }
  }

  @override
  void dispose() {
    ++generation;
    WidgetsBinding.instance.removeObserver(this);
    releasePlayer();
    super.dispose();
  }

  String time(Duration duration) {
    final minutes = duration.inMinutes;
    return '$minutes:${(duration.inSeconds % 60).toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final value = playback?.value ?? const VideoPlayerValue.uninitialized();
    return Scaffold(appBar: AppBar(title: Text(l.proofVideoTitle)), body: SafeArea(child:
      loading ? const Center(child: CircularProgressIndicator()) : error != null
        ? ErrorView(message: error is ApiFailure && (error as ApiFailure).code == 'proof_missing'
            ? l.proofVideoMissing : l.proofVideoUnavailable, onRetry: () => load(refresh: true))
        : Column(children: [
            Expanded(child: Center(child: AspectRatio(
              aspectRatio: value.aspectRatio > 0 ? value.aspectRatio : 16 / 9,
              child: Stack(alignment: Alignment.center, children: [playback!.view(),
                if (value.isBuffering) const CircularProgressIndicator()]),
            ))),
            Text(VisitStrings.videoTitle(widget.reference.proof.stage, widget.reference.proof.takenAt)),
            Padding(padding: const EdgeInsets.all(16), child: Column(children: [
              Slider(value: value.position.inMilliseconds.toDouble().clamp(0.0, value.duration.inMilliseconds.toDouble()).toDouble(),
                max: value.duration.inMilliseconds > 0 ? value.duration.inMilliseconds.toDouble() : 1,
                label: time(value.position),
                onChanged: value.duration.inMilliseconds <= 0 ? null : (position) =>
                  control((player) => player.seekTo(Duration(milliseconds: position.round())))),
              Text('${time(value.position)} / ${time(value.duration)}'),
              IconButton(tooltip: value.isPlaying ? l.proofVideoPause : value.isCompleted ? l.proofVideoReplay : l.proofVideoPlay,
                icon: Icon(value.isPlaying ? Icons.pause_circle : Icons.play_circle), iconSize: 48,
                onPressed: () => control((player) async {
                  if (player.value.isPlaying) { await player.pause(); }
                  else { if (player.value.isCompleted) await player.seekTo(Duration.zero); await player.play(); }
                })),
            ])),
          ])));
  }
}
