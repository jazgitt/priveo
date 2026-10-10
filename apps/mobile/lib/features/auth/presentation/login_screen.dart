import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/auth_controller.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../../core/ui/widgets.dart';
import '../../../l10n/app_localizations.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _id = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _id.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final l = AppLocalizations.of(context);
    if (_id.text.trim().isEmpty || _password.text.isEmpty) {
      setState(() => _error = l.enterIdAndPassword);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      // The router sends the user to their home once the session is set.
      await ref
          .read(authControllerProvider.notifier)
          .login(_id.text.trim(), _password.text);
    } on ApiFailure catch (e) {
      if (mounted) setState(() => _error = e.message ?? l.networkError);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final config = ref.watch(appConfigProvider);
    final demos = {
      l.demoCustomer: 'customer@priveo.test',
      l.demoCrew: '9000000002',
      l.demoAdmin: 'priveopapa',
    };
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: AutofillGroup(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Center(child: BrandLogo(width: 160)),
                    const SizedBox(height: 32),
                    Text(l.loginTitle,
                        style: Theme.of(context).textTheme.headlineMedium),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _id,
                      enabled: !_busy,
                      keyboardType: TextInputType.emailAddress,
                      autofillHints: const [AutofillHints.username],
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(labelText: l.loginIdLabel),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _password,
                      enabled: !_busy,
                      obscureText: _obscure,
                      autofillHints: const [AutofillHints.password],
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: l.passwordLabel,
                        suffixIcon: IconButton(
                          tooltip: _obscure ? l.showPassword : l.hidePassword,
                          icon: Icon(_obscure
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined),
                          onPressed: () =>
                              setState(() => _obscure = !_obscure),
                        ),
                      ),
                    ),
                    // Reserved space, so the layout does not jump.
                    Container(
                      constraints: const BoxConstraints(minHeight: 40),
                      alignment: Alignment.centerLeft,
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: _error == null
                          ? null
                          : Semantics(
                              liveRegion: true,
                              child: Text(_error!,
                                  style: TextStyle(
                                      color: Theme.of(context)
                                          .colorScheme
                                          .error)),
                            ),
                    ),
                    PrimaryButton(
                      label: l.signInButton,
                      busy: _busy,
                      onPressed: _submit,
                    ),
                    if (config.showDemoAccounts) ...[
                      const SizedBox(height: 24),
                      Text(l.demoAccounts,
                          style: Theme.of(context).textTheme.labelMedium),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final e in demos.entries)
                            ActionChip(
                              label: Text(e.key),
                              onPressed: _busy
                                  ? null
                                  : () => setState(() => _id.text = e.value),
                            ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
