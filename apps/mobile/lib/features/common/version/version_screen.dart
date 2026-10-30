import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/providers.dart';
import '../../../core/ui/theme.dart';
import 'version_strings.dart';

/// Opens the Version page over the current screen.
void openVersion(BuildContext context) {
  Navigator.of(
    context,
  ).push(MaterialPageRoute<void>(builder: (_) => const VersionScreen()));
}

/// Which build this is: the app version and build number, whether it is the
/// Test or the Production build, and the API address it talks to. The same
/// page for customers, crew and admins, so a tester can always say which build
/// and which server they are on. The server shows only its project name until
/// the row is tapped three times, then the full address.
class VersionScreen extends ConsumerStatefulWidget {
  const VersionScreen({super.key});

  @override
  ConsumerState<VersionScreen> createState() => _VersionScreenState();
}

class _VersionScreenState extends ConsumerState<VersionScreen> {
  static const _tapsToReveal = 3;
  int _apiTaps = 0;

  /// `https://priveo-api-test.vercel.app` -> `priveo-api-test`. An address
  /// that is not on vercel.app (a local server) is shown in full.
  static String _serverName(String url) {
    final host = Uri.tryParse(url)?.host ?? '';
    return host.endsWith('.vercel.app') ? host.split('.').first : url;
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(appConfigProvider);
    final revealed = _apiTaps >= _tapsToReveal;
    final info = ref.watch(packageInfoProvider).value;
    final rows = <(String, String)>[
      (VersionStrings.app, info?.appName ?? '-'),
      (VersionStrings.environment, config.environmentName),
      (VersionStrings.version, info?.version ?? '-'),
      (VersionStrings.build, info?.buildNumber ?? '-'),
      (
        VersionStrings.api,
        revealed ? config.apiBaseUrl : _serverName(config.apiBaseUrl),
      ),
      (VersionStrings.package, info?.packageName ?? '-'),
      if (config.buildStamp.isNotEmpty)
        (VersionStrings.builtAt, config.buildStamp),
    ];
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    return Scaffold(
      appBar: AppBar(title: const Text(VersionStrings.title)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                child: Column(
                  children: [
                    for (final r in rows)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 110,
                              child: Text(
                                r.$1,
                                style: text.labelMedium?.copyWith(
                                  color: b.mute,
                                ),
                              ),
                            ),
                            Expanded(
                              child: r.$1 == VersionStrings.api
                                  ? GestureDetector(
                                      behavior: HitTestBehavior.opaque,
                                      onTap: () => setState(() => _apiTaps++),
                                      child: Text(r.$2),
                                    )
                                  : SelectableText(r.$2),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                await Clipboard.setData(
                  ClipboardData(
                    text: [for (final r in rows) '${r.$1}: ${r.$2}'].join('\n'),
                  ),
                );
                messenger.showSnackBar(
                  const SnackBar(content: Text(VersionStrings.copied)),
                );
              },
              icon: const Icon(Symbols.content_copy_rounded),
              label: const Text(VersionStrings.copy),
            ),
          ],
        ),
      ),
    );
  }
}

/// The row that opens the Version page from a settings list.
class VersionEntry extends StatelessWidget {
  const VersionEntry({super.key});

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      leading: const Icon(Symbols.info_rounded),
      title: const Text(VersionStrings.settingsEntry),
      subtitle: const Text(VersionStrings.settingsEntryHelp),
      trailing: const Icon(Symbols.chevron_right_rounded),
      onTap: () => openVersion(context),
    ),
  );
}
