import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import 'feedback_sheet.dart';
import 'support_strings.dart';

/// The "side flick" feedback tab on the right edge (FDBK-01). The customer
/// can drag it up and down the edge. There is no way to hide it. Tapping it
/// opens the feedback sheet. It shows only a small icon; the word "Feedback"
/// is its screen-reader label. (No Tooltip: this sits above the Navigator, so
/// there is no Overlay.) Put it over the customer's screens only after
/// onboarding.
class FeedbackSideTab extends StatefulWidget {
  const FeedbackSideTab({super.key, required this.child, this.onOpen});

  final Widget child;

  /// Replaces opening the feedback sheet. For tests.
  final VoidCallback? onOpen;

  @override
  State<FeedbackSideTab> createState() => _FeedbackSideTabState();
}

class _FeedbackSideTabState extends State<FeedbackSideTab> {
  static const _height = 44.0;
  static const _width = 34.0;
  static const _radius = BorderRadius.horizontal(left: Radius.circular(14));

  /// The tab's top as a share of the free height, so a resize keeps it in
  /// place on the edge. Starts a little below the middle.
  double _position = 0.55;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return LayoutBuilder(
      builder: (context, box) {
        final free = (box.maxHeight - _height).clamp(1.0, double.infinity);
        return Stack(
          children: [
            widget.child,
            Positioned(
              right: 0,
              top: free * _position,
              child: GestureDetector(
                onVerticalDragUpdate: (d) => setState(() {
                  _position = (_position + d.delta.dy / free).clamp(0.0, 1.0);
                }),
                child: Semantics(
                  button: true,
                  label: t('support_feedback_tab'),
                  child: Material(
                    color: scheme.primary,
                    elevation: 4,
                    borderRadius: _radius,
                    child: InkWell(
                      borderRadius: _radius,
                      onTap: widget.onOpen ?? () => showFeedbackSheet(context),
                      child: SizedBox(
                        width: _width,
                        height: _height,
                        child: Center(
                          child: Icon(
                            Symbols.feedback_rounded,
                            size: 20,
                            color: scheme.onPrimary,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
