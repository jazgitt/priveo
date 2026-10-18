import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/auth/session.dart';
import '../../core/ui/tokens.g.dart';
import '../../core/ui/widgets.dart';
import '../auth/presentation/auth_strings.dart';
import '../admin_quick/home/admin_home_data.dart';
import '../crew/home/crew_home_data.dart';
import '../crew/crew_providers.dart';
import '../customer/home/customer_home_data.dart';
import '../customer/onboarding/onboarding_review_screen.dart';
import 'showroom_painter.dart';
import 'splash_strings.dart';
import 'startup_progress.dart';

/// Opens the app in two parts (docs/design/Priveo Showroom Splash.html).
///
/// 1. A showroom scene plays for [introDuration]: a gold line-art car draws
///    itself under a spotlight, then the Priveo logo rises beneath it.
/// 2. A thin progress bar then shows how far startup has really got: the saved
///    sign-in has been read, and the first screen of the signed-in role has
///    loaded. The real work starts when the app starts, so most of it is done
///    during the scene.
///
/// A signed-in phone then goes to its role home. A phone with no sign-in stays
/// on this screen: the bar gives way to "Get started" and "Already a member?
/// Log in" at the bottom, so the app has one entry screen. Both open the email
/// step of sign-in. A first screen that fails or takes
/// longer than [giveUpAfter] does not hold the app: the home screen shows its
/// own error and retry. With reduce-motion on, the scene is skipped.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  static const introDuration = Duration(seconds: 3);
  static const giveUpAfter = Duration(seconds: 12);
  static const slowAfter = Duration(seconds: 8);

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _intro;
  late final AnimationController _barIn;
  late final AnimationController _ctaIn;
  late final Ticker _ticker;
  final ValueNotifier<double> _fill = ValueNotifier(0);
  final ValueNotifier<String> _label = ValueNotifier(SplashStrings.checking);

  bool _started = false;
  bool _introDone = false;
  bool _left = false;
  bool _ctas = false;
  bool _sessionResolved = false;
  List<bool> _loads = const [];
  Role? _role;
  Duration _now = Duration.zero;
  Duration _last = Duration.zero;
  Duration? _sessionAt;
  double _real = 0;

  @override
  void initState() {
    super.initState();
    _intro = AnimationController(vsync: this, duration: SplashScreen.introDuration);
    _barIn = AnimationController(vsync: this, duration: const Duration(milliseconds: 300));
    _ctaIn = AnimationController(vsync: this, duration: const Duration(milliseconds: 500));
    _ticker = createTicker(_tick);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (MediaQuery.of(context).disableAnimations) {
      _intro.value = 1;
      _finishIntro();
    } else {
      _intro.forward().whenComplete(_finishIntro);
    }
    _ticker.start();
  }

  void _finishIntro() {
    _introDone = true;
    _barIn.forward();
  }

  /// Runs every frame until the bar is full: moves the bar towards what has
  /// really happened, and leaves when the scene and the loading are both done.
  void _tick(Duration elapsed) {
    _now = elapsed;
    // Nobody is signed in: the scene is over, so offer the two buttons.
    if (_introDone && _sessionResolved && _loads.isEmpty && !_ctas) {
      _ticker.stop();
      setState(() => _ctas = true);
      _ctaIn.forward();
      return;
    }
    final dt = (elapsed - _last).inMicroseconds / 1e6;
    _last = elapsed;
    if (_sessionResolved) _sessionAt ??= elapsed;
    final gaveUp = elapsed > SplashScreen.giveUpAfter;
    final target = startupTarget(
      sinceStart: elapsed,
      sessionResolvedAt: _sessionAt,
      // A load that has not finished by the give-up time no longer holds the app.
      loads: gaveUp ? const [] : _loads,
    );
    final ease = 1 - math.exp(-dt * 7);
    _real = math.max(_real, _real + (target - _real) * ease);
    if (_introDone) {
      final f = _fill.value;
      _fill.value = math.min(1, math.max(f, f + (_real - f) * (1 - math.exp(-dt * 9))));
    }
    final done = target >= 1 && _real > .995;
    if (done) _real = 1;
    if (_introDone && done && _loads.isNotEmpty && _fill.value > .995) {
      _fill.value = 1;
      _ticker.stop();
      _leave();
    }
    _label.value = _wording(done: done);
  }

  String _wording({required bool done}) {
    if (done) return SplashStrings.ready;
    if (_now > SplashScreen.slowAfter) return SplashStrings.slow;
    if (!_sessionResolved) return SplashStrings.checking;
    return switch (_role) {
      Role.customer => SplashStrings.loadingHome,
      Role.crew => SplashStrings.loadingVisits,
      Role.admin => SplashStrings.loadingAdmin,
      null => SplashStrings.ready,
    };
  }

  /// Both buttons open the email step of sign-in.
  void _openSignIn() {
    if (_left || !mounted) return;
    _left = true;
    context.go('/login');
  }

  void _leave() {
    if (_left || !mounted) return;
    _left = true;
    final session = ref.read(authControllerProvider).value;
    context.go(session == null ? '/login' : session.role.homePath);
  }

  @override
  void dispose() {
    _ticker.dispose();
    _intro.dispose();
    _barIn.dispose();
    _ctaIn.dispose();
    _fill.dispose();
    _label.dispose();
    super.dispose();
  }

  /// What the role's first screen needs, watched so it loads now and the screen
  /// finds it ready. One entry for each load: true once it has finished, good
  /// or bad. A customer who has not confirmed their details opens on the review
  /// screen, so its data is loaded too, once the home says that is where they go.
  List<bool> _firstScreen(Session s) {
    bool settled(AsyncValue<Object?> v) => !v.isLoading;
    switch (s.role) {
      case Role.customer:
        final home = ref.watch(customerHomeProvider);
        final review = home.value != null && !home.value!.onboardingConfirmed;
        return [
          settled(home),
          if (review) settled(ref.watch(onboardingProvider)),
          if (review) settled(ref.watch(onboardingSummaryProvider)),
        ];
      case Role.crew:
        final key = visitsKey(ref.read(crewDayProvider));
        return [
          settled(ref.watch(crewVisitsProvider(key))),
          settled(ref.watch(crewProfileProvider)),
        ];
      case Role.admin:
        return [settled(ref.watch(adminHomeProvider))];
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    _sessionResolved = !auth.isLoading;
    final session = auth.value;
    _role = session?.role;
    _loads = session == null ? const [] : _firstScreen(session);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: DarkTokens.app,
        body: Semantics(
          label: 'Priveo',
          child: LayoutBuilder(builder: (context, box) {
            final w = box.maxWidth, h = box.maxHeight;
            return Stack(children: [
              Positioned.fill(child: CustomPaint(painter: ShowroomPainter(_intro))),
              Positioned(
                left: w * .10,
                right: w * .10,
                top: h * .47,
                child: AnimatedBuilder(
                  animation: _intro,
                  builder: (_, _) => _Logo(t: _intro.value, width: w * .8, h: h),
                ),
              ),
              Positioned(
                left: 0,
                right: 0,
                bottom: h * .19,
                child: AnimatedBuilder(
                  animation: _intro,
                  builder: (_, _) => _Tagline(t: _intro.value, w: w, h: h),
                ),
              ),
              Positioned(
                left: 0,
                right: 0,
                bottom: h * .04,
                child: _ctas
                    ? FadeTransition(
                        opacity: CurvedAnimation(parent: _ctaIn, curve: Curves.easeOut),
                        child: _Welcome(
                          onGetStarted: _openSignIn,
                          onLogIn: _openSignIn,
                          width: w,
                        ),
                      )
                    : FadeTransition(
                        opacity: _barIn,
                        child: _Progress(fill: _fill, label: _label, width: w * .26),
                      ),
              ),
            ]);
          }),
        ),
      ),
    );
  }
}

const double _span = ShowroomPainter.span;

/// 0 to 1 for an animation that starts [delay] seconds into the design's
/// timeline and lasts [dur] seconds.
double _p(double t, double delay, double dur, [Curve curve = Curves.linear]) =>
    curve.transform(((t * _span - delay) / dur).clamp(0.0, 1.0));

class _Inset extends CustomClipper<Rect> {
  const _Inset({this.left = 0, this.top = 0, this.right = 0});
  final double left, top, right;

  @override
  Rect getClip(Size s) => Rect.fromLTRB(
      s.width * left, s.height * top, s.width * (1 - right), s.height);

  @override
  bool shouldReclip(_Inset o) =>
      o.left != left || o.top != top || o.right != right;
}

/// The Priveo mark rises, then the name wipes in from the left, then
/// "Car Concierge" opens from the middle.
class _Logo extends StatelessWidget {
  const _Logo({required this.t, required this.width, required this.h});
  final double t, width, h;

  @override
  Widget build(BuildContext context) {
    final mark = _p(t, 2, 1.3, const Cubic(.2, .7, .2, 1));
    final word = _p(t, 2.7, 1.2, const Cubic(.6, .05, .2, 1));
    final sub = _p(t, 3.3, 1.1, const Cubic(.6, .05, .2, 1));
    Widget img(String name, double w) => Image.asset(
        'assets/brand/$name.png', width: w, fit: BoxFit.fitWidth, excludeFromSemantics: true);
    return Column(children: [
      Opacity(
        opacity: mark,
        child: Transform.translate(
          offset: Offset(0, (1 - mark) * h * .02),
          child: Transform.scale(
            scale: .96 + .04 * mark,
            child: ClipRect(
              clipper: _Inset(top: 1 - mark),
              child: img('splash_mark', width * .389),
            ),
          ),
        ),
      ),
      SizedBox(height: width * .0125),
      Opacity(
        opacity: word,
        child: ClipRect(clipper: _Inset(right: 1 - word), child: img('splash_word', width)),
      ),
      SizedBox(height: width * .0375),
      Opacity(
        opacity: sub,
        child: ClipRect(
          clipper: _Inset(left: (1 - sub) / 2, right: (1 - sub) / 2),
          child: img('splash_sub', width),
        ),
      ),
    ]);
  }
}

class _Tagline extends StatelessWidget {
  const _Tagline({required this.t, required this.w, required this.h});
  final double t, w, h;

  @override
  Widget build(BuildContext context) {
    final p = _p(t, 3.7, 1.1, const Cubic(.25, .1, .25, 1));
    return Opacity(
      opacity: p,
      child: Transform.translate(
        offset: Offset(0, (1 - p) * h * .016),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: w * .08),
          child: Text(
            SplashStrings.tagline,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: 'Cormorant Garamond',
              fontStyle: FontStyle.italic,
              fontWeight: FontWeight.w500,
              fontSize: w * .052,
              height: 1.35,
              color: const Color(0xFFEFE6D2).withValues(alpha: .82),
            ),
          ),
        ),
      ),
    );
  }
}

/// The two ways in, for a phone with nobody signed in (AUTH-01).
class _Welcome extends StatelessWidget {
  const _Welcome({required this.onGetStarted, required this.onLogIn, required this.width});
  final VoidCallback onGetStarted, onLogIn;
  final double width;

  @override
  Widget build(BuildContext context) {
    const text = AuthText();
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 380),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: math.max(24, width * .1)),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            PrimaryButton(label: text.getStarted, onPressed: onGetStarted),
            const SizedBox(height: 6),
            TextButton(
              onPressed: onLogIn,
              style: TextButton.styleFrom(foregroundColor: ShowroomPainter.goldHi),
              child: Text(text.alreadyMember),
            ),
          ]),
        ),
      ),
    );
  }
}

/// A hairline track that fills with the real startup progress, and says what
/// is being waited for.
class _Progress extends StatelessWidget {
  const _Progress({required this.fill, required this.label, required this.width});
  final ValueNotifier<double> fill;
  final ValueNotifier<String> label;
  final double width;

  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
        ValueListenableBuilder<double>(
          valueListenable: fill,
          builder: (_, v, _) => Semantics(
            label: 'Loading',
            value: '${(v * 100).round()} percent',
            child: Container(
              width: width,
              height: 2,
              color: Colors.white.withValues(alpha: .14),
              alignment: Alignment.centerLeft,
              child: FractionallySizedBox(
                widthFactor: v,
                child: const DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: [Color(0x00D6B56A), ShowroomPainter.goldHi, ShowroomPainter.gold]),
                  ),
                  child: SizedBox.expand(),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        ValueListenableBuilder<String>(
          valueListenable: label,
          builder: (_, text, _) => Text(
            text,
            style: const TextStyle(fontSize: 11, letterSpacing: 1.4, color: Color(0xFF8C857C)),
          ),
        ),
      ]);
}

/// Used by tests and the native splash colour.
const splashBackgroundDark = DarkTokens.app;
