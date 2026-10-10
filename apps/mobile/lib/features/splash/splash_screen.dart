import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/ui/theme.dart';
import '../../core/ui/tokens.g.dart';
import '../../core/ui/widgets.dart';
import '../../l10n/app_localizations.dart';

/// Animated logo: fade and scale in, a gold rule draws under it, about two
/// seconds. With reduce-motion on it is a short fade. Then it goes to login
/// or the role home.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  bool _started = false;
  bool _reduceMotion = false;
  bool _animationDone = false;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _reduceMotion = MediaQuery.of(context).disableAnimations;
    _c.duration = _reduceMotion
        ? const Duration(milliseconds: 400)
        : const Duration(milliseconds: 2000);
    _c.forward().whenComplete(() {
      _animationDone = true;
      _maybeLeave();
    });
  }

  void _maybeLeave() {
    if (!mounted || !_animationDone) return;
    final auth = ref.read(authControllerProvider);
    if (auth.isLoading) return;
    final session = auth.value;
    context.go(session == null ? '/login' : session.role.homePath);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(authControllerProvider, (_, _) => _maybeLeave());
    final gold = context.brand.gold;
    final fade = CurvedAnimation(
        parent: _c, curve: const Interval(0, 0.5, curve: Curves.easeOut));
    final scale = Tween<double>(begin: _reduceMotion ? 1 : 0.88, end: 1)
        .animate(fade);
    final rule = CurvedAnimation(
        parent: _c, curve: const Interval(0.45, 0.9, curve: Curves.easeInOut));

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: Center(
        child: Semantics(
          label: AppLocalizations.of(context).appName,
          child: FadeTransition(
            opacity: fade,
            child: ScaleTransition(
              scale: scale,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const BrandLogo(width: 200),
                  const SizedBox(height: 16),
                  AnimatedBuilder(
                    animation: rule,
                    builder: (_, _) => Container(
                      width: 140 * (_reduceMotion ? 1 : rule.value),
                      height: 2,
                      color: gold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Used by tests and the native splash colour.
const splashBackgroundDark = DarkTokens.app;
