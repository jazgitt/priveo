import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/ui/widgets.dart';

/// The logo is whole: three images, none cut off, and a height that follows the width.
void main() {
  testWidgets('shows the monogram, the name and Car Concierge in full', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: Center(child: BrandLogo(width: 200)))));
    final names = tester
        .widgetList<Image>(find.byType(Image))
        .map((i) => (i.image as AssetImage).assetName.split('/').last)
        .toList();
    expect(names, ['splash_mark.png', 'splash_word.png', 'splash_sub.png']);
    // Nothing clips it, and the box is as tall as the three images and the gaps.
    expect(find.descendant(of: find.byType(BrandLogo), matching: find.byType(ClipRect)), findsNothing);
    final box = tester.getRect(find.byType(BrandLogo));
    expect(box.width, 200);
    expect(box.height, closeTo(BrandLogo.heightFor(200), 0.01));
    final last = tester.getRect(find.byType(Image).last);
    expect(last.bottom, lessThanOrEqualTo(box.bottom + 0.01));
  });

  test('its height follows its width', () {
    expect(BrandLogo.heightFor(400), closeTo(2 * BrandLogo.heightFor(200), 1e-9));
    expect(BrandLogo.heightFor(200), closeTo(102.6, 0.1));
  });
}
