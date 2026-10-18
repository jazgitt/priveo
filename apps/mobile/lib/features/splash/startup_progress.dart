import 'dart:math' as math;

/// How far the app has got with starting up, from what has really happened.
///
/// Startup has two real parts: reading the saved sign-in from the phone, and,
/// when someone is signed in, loading what their first screen needs. That can
/// be several loads (a customer who has not confirmed their details also needs
/// the review data). The first part has [sessionShare] of the bar; the loads
/// share the rest equally. A finished load fills its share at once. While loads
/// run, the bar creeps towards 90% of one share, so it keeps moving but never
/// claims more than has happened. When everything is done the target is 1.
const double sessionShare = 0.3;

/// A step with no known length creeps like this: fast at first, then slower.
double _creep(Duration sinceStart, Duration settle) {
  final t = sinceStart.inMilliseconds / settle.inMilliseconds;
  return 0.9 * (1 - math.exp(-t));
}

/// The share of the bar that is true now, from 0 to 1.
///
/// [sinceStart] is the time since the app began starting up, and
/// [sessionResolvedAt] the time the saved sign-in was read (null while it is
/// still being read). [loads] has one entry for each load the first screen
/// needs, true when that load has finished, failed or been given up on. It is
/// empty when nobody is signed in.
double startupTarget({
  required Duration sinceStart,
  required Duration? sessionResolvedAt,
  required List<bool> loads,
}) {
  if (sessionResolvedAt == null) {
    return sessionShare * _creep(sinceStart, const Duration(milliseconds: 800));
  }
  if (loads.every((done) => done)) return 1;
  final share = (1 - sessionShare) / loads.length;
  final finished = loads.where((done) => done).length;
  final inData = sinceStart - sessionResolvedAt;
  final creep = _creep(inData.isNegative ? Duration.zero : inData,
      const Duration(milliseconds: 2500));
  return sessionShare + share * finished + share * creep;
}
