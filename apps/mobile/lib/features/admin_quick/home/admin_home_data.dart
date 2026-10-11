import '../data/admin_quick_providers.dart';

/// The admin home on real data. It reads `/v1/admin/home` through the
/// hand-written repository, because the quick actions need fields (open
/// complaints, societies) that the generated client may not have yet.
final adminHomeProvider = adminQuickHomeProvider;
