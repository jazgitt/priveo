import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../auth/session.dart';
import '../providers.dart';
import '../routing/router.dart';
import 'analytics_consent.dart';

/// Replaces ids in a path so a screen name never carries a record id.
String screenNameFor(String path) => path
    .replaceAll(RegExp(r'[0-9a-fA-F]{8}-[0-9a-fA-F-]{27}'), ':id')
    .replaceAll(RegExp(r'/\d+(?=/|$)'), '/:id');

/// Whether replay may run for [role]. Crew are left out for now: they see
/// vehicle photos and job notes.
bool replayAllowedFor(Role role) => role != Role.crew;

/// Connects sign-in and navigation to [analyticsProvider]. Watch it once from
/// the app widget.
final analyticsBindingProvider = Provider<void>((ref) {
  final analytics = ref.read(analyticsProvider);
  if (!analytics.isActive) return;

  ref.listen<AsyncValue<Session?>>(authControllerProvider, (prev, next) {
    final was = prev?.value;
    final now = next.value;
    if (now != null) {
      final id = now.loginId;
      if (id != null && id != was?.loginId) {
        analytics.identify(id, role: now.role.name);
        final shared = ref.read(analyticsEnabledProvider).value ?? true;
        if (shared && replayAllowedFor(now.role)) analytics.startReplay();
      }
    } else if (was != null) {
      analytics.stopReplay();
      analytics.reset();
    }
  }, fireImmediately: true);

  final router = ref.read(routerProvider);
  final info = router.routeInformationProvider;
  String? last;
  void onRoute() {
    final name = screenNameFor(info.value.uri.path);
    if (name == last) return;
    last = name;
    analytics.screen(name);
  }

  info.addListener(onRoute);
  ref.onDispose(() => info.removeListener(onRoute));
});
