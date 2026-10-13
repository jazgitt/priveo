import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:video_player/video_player.dart';
import 'package:priveo/core/network/api_failure.dart';
import 'package:priveo/core/providers.dart';
import 'package:priveo/core/ui/theme.dart';
import 'package:priveo/features/customer/data/customer_reads_repository.dart';
import 'package:priveo/features/customer/visit/proof_video_screen.dart';
import 'package:priveo/l10n/app_localizations.dart';

class FakePlayer extends ProofVideoPlayback {
  VideoPlayerValue state = const VideoPlayerValue.uninitialized();
  Completer<void>? held;
  bool fail = false, disposed = false;
  int played = 0, paused = 0;
  Duration? sought;
  @override
  VideoPlayerValue get value => state;
  @override
  Future<void> initialize() async {
    if (held != null) await held!.future;
    if (disposed) return;
    if (fail) throw const ApiFailure(code: 'expired_url');
    state = const VideoPlayerValue(duration: Duration(seconds: 30),
      size: Size(160, 90), isInitialized: true);
    notifyListeners();
  }
  @override
  Future<void> play() async { played++; state = state.copyWith(isPlaying: true); notifyListeners(); }
  @override
  Future<void> pause() async { paused++; state = state.copyWith(isPlaying: false); notifyListeners(); }
  @override
  Future<void> seekTo(Duration position) async { sought = position; state = state.copyWith(position: position, isCompleted: false); notifyListeners(); }
  @override
  Widget view() => const SizedBox.expand(child: Text('Native video surface'));
  @override
  void dispose() { disposed = true; super.dispose(); }
}

class FakeReads extends Fake implements CustomerReadsRepository {
  int calls = 0;
  VisitDetailDto visitData = detail([
    const ProofDto(id: 'different', kind: 'video', url: '/media/different'),
    const ProofDto(id: 'proof1', kind: 'video', url: '/media/refreshed?token=new'),
  ]);
  @override
  Future<VisitDetailDto> visit(String id) async { calls++; return visitData; }
}

VisitDetailDto detail(List<ProofDto> proof) => VisitDetailDto(id: 'visit1', vehicleId: 'v1',
  vehicleRegistration: 'HR01ZZ1234', vehicleModel: 'Nexon', date: DateTime(2026, 11, 15),
  status: 'Completed', jobs: [JobDto(id: 'job1', service: 'Deep Spa', status: 'Done', proof: proof)]);

const reference = ProofVideoReference(visitId: 'visit1', jobId: 'job1',
  proof: ProofDto(id: 'proof1', kind: 'video', url: '/media/original?token=old'), videoIndex: 0);

Future<void> app(WidgetTester tester, List<FakePlayer> players, FakeReads reads,
    List<Uri> urls, {bool settle = true}) async {
  var index = 0;
  await tester.pumpWidget(ProviderScope(overrides: [
    dioProvider.overrideWithValue(Dio(BaseOptions(baseUrl: 'https://api.example',
      headers: {'Authorization': 'Bearer should-not-go-to-media'}))),
    customerReadsProvider.overrideWithValue(reads),
    proofVideoPlaybackProvider.overrideWithValue((uri) { urls.add(uri); return players[index++]; }),
  ], child: MaterialApp(theme: customerTheme,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: const ProofVideoScreen(reference: reference))));
  if (settle) { await tester.pumpAndSettle(); } else { await tester.pump(); }
}

void main() {
  test('refresh keeps the original media ID when proof ordering changes', () {
    final updated = reference.refreshed(detail([
      const ProofDto(id: 'different', kind: 'video', url: '/other'),
      const ProofDto(id: 'proof1', kind: 'video', url: '/fresh'),
    ]));
    expect(updated.url, '/fresh');
    expect(() => reference.refreshed(detail([])), throwsA(isA<ApiFailure>()));
  });
  testWidgets('plays and pauses in-app and seeks within the video', (tester) async {
    final player = FakePlayer(); final urls = <Uri>[];
    await app(tester, [player], FakeReads(), urls);
    expect(urls.single.toString(), 'https://api.example/media/original?token=old');
    expect(find.text('Native video surface'), findsOneWidget);
    expect(player.played, 0);
    await tester.tap(find.byTooltip('Play')); await tester.pump();
    expect(player.played, 1);
    await tester.tap(find.byTooltip('Pause')); await tester.pump();
    expect(player.paused, 1);
    tester.widget<Slider>(find.byType(Slider)).onChanged!(12000);
    await tester.pump(); expect(player.sought, const Duration(seconds: 12));
    await tester.pumpWidget(const SizedBox.shrink());
    expect(player.disposed, isTrue);
  });
  testWidgets('expired URL retries through owned visit reads and replaces the player', (tester) async {
    final first = FakePlayer()..fail = true; final second = FakePlayer();
    final reads = FakeReads(); final urls = <Uri>[];
    await app(tester, [first, second], reads, urls);
    expect(find.textContaining('The video could not be played'), findsOneWidget);
    await tester.tap(find.text('Try again')); await tester.pumpAndSettle();
    expect(reads.calls, greaterThanOrEqualTo(1));
    expect(urls.last.toString(), 'https://api.example/media/refreshed?token=new');
    expect(first.disposed, isTrue);
    expect(find.text('Native video surface'), findsOneWidget);
  });
  testWidgets('a removed video does not play a different proof item', (tester) async {
    final player = FakePlayer()..fail = true;
    final reads = FakeReads()..visitData = detail([
      const ProofDto(id: 'different', kind: 'video', url: '/different'),
    ]);
    final urls = <Uri>[];
    await app(tester, [player], reads, urls);
    await tester.tap(find.text('Try again')); await tester.pumpAndSettle();
    expect(find.text('This video is no longer available for this visit.'), findsOneWidget);
    expect(urls, hasLength(1));
  });
  testWidgets('app backgrounding pauses playback', (tester) async {
    final player = FakePlayer(); await app(tester, [player], FakeReads(), []);
    await tester.tap(find.byTooltip('Play')); await tester.pump();
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump(); expect(player.paused, 1);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump(); expect(player.played, 1);
  });
  testWidgets('disposing while loading cancels the timeout and releases resources', (tester) async {
    final player = FakePlayer()..held = Completer<void>();
    await app(tester, [player], FakeReads(), [], settle: false);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    expect(player.disposed, isTrue);
    player.held!.complete(); await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
