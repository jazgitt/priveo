import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';

/// A media URL against the API base URL. Absolute URLs pass through. The dev
/// object store sends signed URLs relative to the API.
String absoluteMediaUrl(String base, String url) {
  if (url.startsWith('http://') || url.startsWith('https://') || base.isEmpty) {
    return url;
  }
  final root = base.endsWith('/') ? base.substring(0, base.length - 1) : base;
  return url.startsWith('/') ? '$root$url' : '$root/$url';
}

/// A network image for a signed media URL. A failed load shows [fallback].
class MediaImage extends ConsumerWidget {
  const MediaImage(
    this.url, {
    super.key,
    this.fit = BoxFit.cover,
    this.width,
    this.height,
    this.fallback,
  });

  final String url;
  final BoxFit fit;
  final double? width;
  final double? height;
  final Widget? fallback;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final base = ref.watch(dioProvider).options.baseUrl;
    return Image.network(
      absoluteMediaUrl(base, url),
      fit: fit,
      width: width,
      height: height,
      errorBuilder: (context, error, stack) =>
          fallback ?? const SizedBox.shrink(),
    );
  }
}
