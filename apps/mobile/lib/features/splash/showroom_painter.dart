import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/animation.dart';
import 'package:flutter/rendering.dart';

/// The splash's showroom: a spotlight, a floor glow and a gold line-art sedan
/// that draws itself, its wheels spinning in, with a polish sheen across the
/// paint (docs/design/Priveo Showroom Splash.html).
///
/// The design's timeline runs 4.8 seconds. [progress] runs 0 to 1 over the real
/// duration (3 seconds), so every delay and duration is scaled by the same
/// factor and the sequence is the same, only quicker.
class ShowroomPainter extends CustomPainter {
  ShowroomPainter(this.progress) : super(repaint: progress);

  final Animation<double> progress;

  /// Seconds of the design's timeline.
  static const double span = 4.8;

  static const gold = Color(0xFFD6B56A);
  static const goldHi = Color(0xFFF1D98E);
  static const goldLo = Color(0xFF9C7A34);
  static const _cream = Color(0xFFFFF4D6);

  /// 0 to 1 for an animation that starts [delay] seconds in and lasts [dur]
  /// seconds, on the design's timeline.
  double _p(double delay, double dur, [Curve curve = Curves.linear]) =>
      curve.transform(((progress.value * span - delay) / dur).clamp(0.0, 1.0));

  static const _ease = Cubic(.25, .1, .25, 1);
  static const _body = Cubic(.65, .05, .25, 1);

  static final Path _bodyPath = Path()
    ..moveTo(26, 98)
    ..lineTo(24, 82)
    ..cubicTo(24, 73, 32, 69, 50, 66)
    ..lineTo(100, 58)
    ..cubicTo(120, 54, 136, 38, 160, 34)
    ..cubicTo(180, 31, 222, 31, 244, 34)
    ..cubicTo(268, 40, 288, 54, 312, 60)
    ..lineTo(352, 67)
    ..cubicTo(368, 70, 374, 76, 375, 86)
    ..lineTo(376, 98)
    ..lineTo(333, 98)
    ..arcToPoint(const Offset(279, 98), radius: const Radius.circular(27), clockwise: false)
    ..lineTo(123, 98)
    ..arcToPoint(const Offset(69, 98), radius: const Radius.circular(27), clockwise: false)
    ..close();

  static final Path _windowFront = Path()
    ..moveTo(118, 54)
    ..cubicTo(132, 48, 144, 40, 163, 37.5)
    ..lineTo(197, 37.5)
    ..lineTo(197, 54)
    ..close();
  static final Path _windowRear = Path()
    ..moveTo(205, 37.5)
    ..lineTo(241, 37.5)
    ..cubicTo(259, 42, 275, 51, 292, 55)
    ..lineTo(205, 55)
    ..close();

  Paint _stroke(double width, {Color? color, Shader? shader}) => Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = width
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..color = color ?? const Color(0xFFFFFFFF)
    ..shader = shader;

  /// The first [t] of a path's length, as a path.
  static Path _partial(Path path, double t) {
    if (t >= 1) return path;
    final out = Path();
    for (final m in path.computeMetrics()) {
      out.addPath(m.extractPath(0, m.length * t), Offset.zero);
    }
    return out;
  }

  /// Draws with the given opacity, as one piece.
  void _faded(Canvas canvas, Rect bounds, double opacity, VoidCallback draw) {
    if (opacity <= 0) return;
    if (opacity >= 1) return draw();
    canvas.saveLayer(bounds, Paint()..color = Color.fromRGBO(0, 0, 0, opacity));
    draw();
    canvas.restore();
  }

  void _glow(Canvas canvas, Offset center, double rx, double ry, Color color, double opacity,
      {double stop = 1}) {
    if (opacity <= 0) return;
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.scale(1, ry / rx);
    final shader = ui.Gradient.radial(Offset.zero, rx, [
      color.withValues(alpha: color.a * opacity),
      color.withValues(alpha: 0),
    ], [0, stop]);
    canvas.drawCircle(Offset.zero, rx, Paint()..shader = shader);
    canvas.restore();
  }

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    canvas.drawRect(Offset.zero & size, Paint()..color = const Color(0xFF0D0D10));
    // The first frame is the native launch colour; the showroom fades in over it.
    final lights = _p(0, .5);
    _faded(canvas, Offset.zero & size, lights, () {
      canvas.drawRect(
        Offset.zero & size,
        Paint()
          ..shader = ui.Gradient.linear(Offset.zero, Offset(0, h), const [
            Color(0xFF141416), Color(0xFF0A0A0B), Color(0xFF050506),
          ], const [0, .52, 1]),
      );
    });
    // Spotlight from the top, glow on the floor, and a halo that comes up later.
    _glow(canvas, Offset(w / 2, 0), w * .55, h * .72, const Color(0x33F1D98E), _p(.2, 1.6), stop: .72);
    _glow(canvas, Offset(w / 2, h * .30 + h * .12), w * .6, h * .12, const Color(0x29D6B56A), _p(.5, 1.6));
    _glow(canvas, Offset(w / 2, h * .44 + w * .31), w * .48, w * .31, const Color(0x1AD6B56A), _p(2, 1.8));

    _car(canvas, size);

    // Vignette over everything drawn here: an ellipse, clear in the middle.
    canvas.save();
    canvas.translate(w / 2, h * .4);
    canvas.scale(1, (h * .9) / (w * 1.2));
    canvas.drawRect(
      Rect.fromLTRB(-w * 2, -h * 4, w * 2, h * 4),
      Paint()
        ..shader = ui.Gradient.radial(Offset.zero, w * 1.2,
            const [Color(0x00000000), Color(0x8C000000)], const [.55, 1]),
    );
    canvas.restore();
  }

  void _car(Canvas canvas, Size size) {
    final carW = size.width * .86;
    final s = carW / 400;
    canvas.save();
    canvas.translate(size.width * .07, size.height * .19);
    canvas.scale(s);
    const view = Rect.fromLTWH(-20, -20, 440, 210);

    // Reflection on the floor: the body upside down, fading out downwards.
    final refl = _p(1.8, 1.4, _ease);
    if (refl > 0) {
      canvas.saveLayer(const Rect.fromLTWH(0, 119, 400, 51), Paint());
      canvas.save();
      canvas.translate(0, 238);
      canvas.scale(1, -1);
      _faded(canvas, view, .3 * refl, () => canvas.drawPath(_bodyPath, _stroke(1.4, color: gold)));
      canvas.restore();
      canvas.drawRect(
        const Rect.fromLTWH(0, 119, 400, 51),
        Paint()
          ..blendMode = BlendMode.dstIn
          ..shader = ui.Gradient.linear(const Offset(0, 119), const Offset(0, 165), const [
            Color(0xE6FFFFFF), Color(0x00FFFFFF),
          ]),
      );
      canvas.restore();
    }

    // Ground line.
    final ground = _p(.1, 1.4, _ease);
    if (ground > 0) {
      canvas.drawPath(
        _partial(Path()..moveTo(14, 119)..lineTo(386, 119), ground),
        _stroke(1, shader: ui.Gradient.linear(const Offset(14, 0), const Offset(386, 0), const [
          Color(0x00D6B56A), goldHi, Color(0x00D6B56A),
        ], const [0, .5, 1])),
      );
    }

    // Body: outline draws, then the paint fills in.
    final body = _p(.2, 1.9, _body);
    final fill = _p(1.7, 1.0, _ease);
    final box = _bodyPath.getBounds();
    if (fill > 0) {
      _faded(canvas, view, fill, () => canvas.drawPath(
        _bodyPath,
        Paint()..shader = ui.Gradient.linear(box.topCenter, box.bottomCenter, [
          goldHi.withValues(alpha: .14), gold.withValues(alpha: .03),
        ]),
      ));
    }
    if (body > 0) {
      canvas.drawPath(
        _partial(_bodyPath, body),
        _stroke(1.7, shader: ui.Gradient.linear(box.centerLeft, box.centerRight, const [goldLo, goldHi, gold], const [0, .5, 1])),
      );
    }

    // Windows.
    final win = _p(.9, 1.2, _ease);
    if (win > 0) {
      canvas.drawPath(_partial(_windowFront, win), _stroke(1.1, color: gold));
      canvas.drawPath(_partial(_windowRear, win), _stroke(1.1, color: gold));
    }

    // Details: shoulder line, door seam, handles, lamps.
    _faded(canvas, view, _p(1.5, 1, _ease), () {
      canvas.drawPath(Path()..moveTo(40, 76)..cubicTo(140, 70, 260, 70, 360, 76), _stroke(1, color: gold.withValues(alpha: .5)));
      canvas.drawPath(Path()..moveTo(201, 55)..lineTo(201, 92), _stroke(1, color: gold.withValues(alpha: .6)));
      canvas.drawPath(Path()..moveTo(178, 66)..lineTo(190, 66)..moveTo(214, 66)..lineTo(226, 66), _stroke(1.4, color: gold));
      final head = Path()..moveTo(356, 68)..cubicTo(364, 69, 370, 72, 373, 77)..lineTo(357, 75)..close();
      canvas.drawPath(head, Paint()..color = goldHi.withValues(alpha: .5));
      canvas.drawPath(head, _stroke(1, color: goldHi));
      final tail = Path()..moveTo(27, 80)..lineTo(40, 75)..lineTo(40, 81)..close();
      canvas.drawPath(tail, Paint()..color = gold.withValues(alpha: .35));
      canvas.drawPath(tail, _stroke(1, color: gold));
    });

    // The sheen: a slanted band of light crossing the paint, kept inside the body.
    final sheen = _p(2, 1.7, const Cubic(.4, 0, .2, 1));
    if (sheen > 0 && sheen < 1) {
      canvas.save();
      canvas.clipPath(_bodyPath);
      canvas.translate(-140 + 700 * sheen, 0);
      canvas.transform(Float64List.fromList([
        1, 0, 0, 0, math.tan(-24 * math.pi / 180), 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1,
      ]));
      canvas.drawRect(
        const Rect.fromLTWH(0, 20, 70, 100),
        Paint()..shader = ui.Gradient.linear(const Offset(0, 0), const Offset(70, 0), const [
          Color(0x00FFF4D6), Color(0xCCFFF4D6), Color(0x00FFF4D6),
        ], const [0, .5, 1]),
      );
      canvas.restore();
    }

    _wheel(canvas, 96);
    _wheel(canvas, 306);

    // A flare on the headlamp as the sheen arrives.
    final f = _p(1.9, 1.5);
    if (f > 0) {
      final up = f < .4;
      final k = up ? Curves.easeOut.transform(f / .4) : Curves.easeInOut.transform((f - .4) / .6);
      final opacity = up ? k : 1 - (1 - .45) * k;
      final scale = up ? .3 + (1.4 - .3) * k : 1.4 - .4 * k;
      canvas.drawCircle(
        const Offset(364, 74), 16 * scale,
        Paint()..shader = ui.Gradient.radial(const Offset(364, 74), 16 * scale, [
          _cream.withValues(alpha: opacity),
          goldHi.withValues(alpha: .55 * opacity),
          gold.withValues(alpha: 0),
        ], const [0, .35, 1]),
      );
    }
    canvas.restore();
  }

  void _wheel(Canvas canvas, double cx) {
    final ring = _p(1, 1, _ease);
    if (ring <= 0) return;
    final spin = (1 - _p(1, 1.8, const Cubic(.2, .7, .2, 1))) * -300 * math.pi / 180;
    canvas.save();
    canvas.translate(cx, 98);
    canvas.rotate(spin);
    canvas.drawPath(_partial(Path()..addOval(Rect.fromCircle(center: Offset.zero, radius: 21)), ring), _stroke(1.6, color: goldHi));
    _faded(canvas, const Rect.fromLTWH(-24, -24, 48, 48), ring, () {
      canvas.drawCircle(Offset.zero, 14.5, _stroke(.8, color: gold.withValues(alpha: .6)));
      for (var i = 0; i < 5; i++) {
        final a = i * 72 * math.pi / 180 - math.pi / 2;
        canvas.drawLine(Offset(4 * math.cos(a), 4 * math.sin(a)), Offset(13 * math.cos(a), 13 * math.sin(a)), _stroke(1.4, color: gold));
      }
      canvas.drawCircle(Offset.zero, 3, _stroke(1, color: goldHi));
    });
    canvas.restore();
  }

  @override
  bool shouldRepaint(ShowroomPainter old) => old.progress != progress;
}
