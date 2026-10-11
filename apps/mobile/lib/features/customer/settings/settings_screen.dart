import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/ui/theme.dart';
import '../cust_strings.dart';
import '../cust_ui.dart';
import 'notification_prefs_repository.dart';

/// Opens Settings over the current screen.
void openSettings(BuildContext context) {
  Navigator.of(
    context,
  ).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen()));
}

/// Settings holds only the notification switches in MVP (SET-01 to SET-04).
/// Each switch changes on its own and is saved at once.
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  // The value shown while a change is being saved.
  final Map<String, bool> _pending = {};

  Future<void> _change(NotificationPrefDto pref, bool value) async {
    setState(() => _pending[pref.event] = value);
    try {
      await ref
          .read(notificationPrefsRepositoryProvider)
          .set(pref.event, value);
      ref.invalidate(notificationPrefsProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            e is ApiFailure && e.message != null
                ? e.message!
                : CustStrings.settingsSaveFailed,
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _pending.remove(pref.event));
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final b = context.brand;
    final prefs = ref.watch(notificationPrefsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text(CustStrings.settingsHeading)),
      body: SafeArea(
        child: AsyncBody<List<NotificationPrefDto>>(
          value: prefs,
          onRetry: () => ref.invalidate(notificationPrefsProvider),
          builder: (items) => ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                CustStrings.settingsNotifications,
                style: text.titleMedium?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                CustStrings.settingsIntro,
                style: text.bodyMedium?.copyWith(color: b.mute),
              ),
              const SizedBox(height: 12),
              for (final p in items)
                Card(
                  child: SwitchListTile(
                    title: Text(p.title),
                    subtitle: Text(p.description),
                    value: _pending[p.event] ?? p.enabled,
                    onChanged: (v) => _change(p, v),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
