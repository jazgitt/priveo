import 'package:flutter/material.dart';

import '../../../core/ui/theme.dart';

/// The default picture on a vehicle card when the customer has no vehicle
/// photo: a simple side view of a car on a soft background (HOME-02).
class CarIllustration extends StatelessWidget {
  const CarIllustration({super.key});

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    return Semantics(
      image: true,
      label: 'Car illustration',
      child: ExcludeSemantics(
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [b.gold.withValues(alpha: 0.10), b.line.withValues(alpha: 0.35)],
            ),
          ),
          child: CustomPaint(
            painter: _CarPainter(body: b.gold, glass: b.mute, ground: b.line),
            size: Size.infinite,
          ),
        ),
      ),
    );
  }
}

class _CarPainter extends CustomPainter {
  _CarPainter({required this.body, required this.glass, required this.ground});

  final Color body;
  final Color glass;
  final Color ground;

  @override
  void paint(Canvas canvas, Size size) {
    // Draw on a 200 x 100 grid, scaled to fit and centred.
    final scale = (size.width / 200).clamp(0.0, size.height / 100);
    canvas.save();
    canvas.translate((size.width - 200 * scale) / 2, (size.height - 100 * scale) / 2);
    canvas.scale(scale);

    final shadow = Paint()..color = ground;
    canvas.drawOval(const Rect.fromLTWH(30, 78, 140, 8), shadow);

    final bodyPaint = Paint()..color = body;
    final bodyPath = Path()
      ..moveTo(22, 70)
      ..lineTo(22, 58)
      ..quadraticBezierTo(24, 50, 40, 47)
      ..lineTo(62, 44)
      ..lineTo(76, 28)
      ..quadraticBezierTo(80, 24, 88, 24)
      ..lineTo(122, 24)
      ..quadraticBezierTo(130, 24, 136, 30)
      ..lineTo(150, 44)
      ..lineTo(172, 48)
      ..quadraticBezierTo(180, 50, 180, 60)
      ..lineTo(180, 70)
      ..close();
    canvas.drawPath(bodyPath, bodyPaint);

    final glassPaint = Paint()..color = glass.withValues(alpha: 0.55);
    final windows = Path()
      ..moveTo(70, 44)
      ..lineTo(81, 31)
      ..quadraticBezierTo(83, 29, 88, 29)
      ..lineTo(104, 29)
      ..lineTo(104, 44)
      ..close()
      ..moveTo(110, 44)
      ..lineTo(110, 29)
      ..lineTo(122, 29)
      ..quadraticBezierTo(127, 29, 130, 33)
      ..lineTo(142, 44)
      ..close();
    canvas.drawPath(windows, glassPaint);

    final tyre = Paint()..color = const Color(0xFF1B1B1B);
    final rim = Paint()..color = const Color(0xFFD9D9D9);
    for (final x in const [56.0, 146.0]) {
      canvas.drawCircle(Offset(x, 72), 13, tyre);
      canvas.drawCircle(Offset(x, 72), 6, rim);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(_CarPainter old) =>
      old.body != body || old.glass != glass || old.ground != ground;
}
