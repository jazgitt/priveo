import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../core/auth/auth_controller.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/providers.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../../../l10n/app_localizations.dart';
import '../../support/widgets.dart' show linkOpenerProvider;
import '../data/support_contact.dart';
import 'auth_strings.dart';

/// The steps of signing in. Everyone starts at [id]. A customer who has no
/// password yet, or has forgotten it, goes through [code] and [newPassword]
/// (AUTH-03, AUTH-16). Everyone else goes to [password].
enum _Step { welcome, id, password, code, newPassword }

/// AUTH-12: at least 8 characters, with a letter and a number.
bool isAcceptablePassword(String p) =>
    p.length >= 8 && p.contains(RegExp('[A-Za-z]')) && p.contains(RegExp(r'\d'));

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _id = TextEditingController();
  final _password = TextEditingController();
  final _code = TextEditingController();
  final _newPassword = TextEditingController();
  final _confirm = TextEditingController();
  _Step _step = _Step.welcome;
  bool _notRegistered = false;
  late final _termsTap = TapGestureRecognizer()
    ..onTap = () => openLegalLink(ref, 'terms');
  late final _privacyTap = TapGestureRecognizer()
    ..onTap = () => openLegalLink(ref, 'privacy');
  bool _obscure = true;
  bool _busy = false;
  String? _error;
  String _passwordToken = '';
  int _resendIn = 0;
  Timer? _countdown;

  String get _loginId => _id.text.trim();
  bool get _isEmail => _loginId.contains('@');

  @override
  void dispose() {
    _countdown?.cancel();
    _termsTap.dispose();
    _privacyTap.dispose();
    for (final c in [_id, _password, _code, _newPassword, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  void _go(_Step step) => setState(() {
        _step = step;
        _error = null;
        _notRegistered = false;
        _obscure = true;
        if (step == _Step.id) {
          _countdown?.cancel();
          _password.clear();
        }
        if (step != _Step.newPassword) {
          _newPassword.clear();
          _confirm.clear();
        }
      });

  void _startCountdown(int seconds) {
    _countdown?.cancel();
    setState(() => _resendIn = seconds);
    if (seconds <= 0) return;
    _countdown = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_resendIn <= 1) t.cancel();
      setState(() => _resendIn -= 1);
    });
  }

  /// Runs one call to the API, with the busy state and the error slot.
  Future<void> _run(Future<void> Function() action) async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
      _notRegistered = false;
    });
    try {
      await action();
    } on ApiFailure catch (e) {
      if (mounted) {
        setState(() {
          _error = e.message ?? l.networkError;
          _notRegistered = e.code == 'email_not_registered';
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _continue() async {
    if (_loginId.isEmpty) {
      setState(() => _error = AppLocalizations.of(context).enterId);
      return;
    }
    if (_isEmail && !isPlausibleEmail(_loginId)) {
      setState(() => _error = const AuthText().emailInvalid);
      return;
    }
    await _run(() async {
      final next = await ref.read(authRepositoryProvider).start(_loginId);
      if (!mounted) return;
      if (next.next == 'code') {
        _openCode(next.resendInSeconds);
      } else {
        _go(_Step.password);
      }
    });
  }

  void _openCode(int resendIn) {
    _code.clear();
    _go(_Step.code);
    _startCountdown(resendIn);
  }

  Future<void> _signIn() async {
    if (_password.text.isEmpty) {
      setState(() => _error = AppLocalizations.of(context).enterPassword);
      return;
    }
    // The router sends the user to their home once the session is set.
    await _run(() => ref
        .read(authControllerProvider.notifier)
        .login(_loginId, _password.text));
  }

  /// "Forgot password" and "Resend code".
  Future<void> _sendCode() => _run(() async {
        final wait = await ref.read(authRepositoryProvider).sendCode(_loginId);
        if (mounted) _openCode(wait);
      });

  Future<void> _verify() async {
    if (_code.text.length != 6) {
      setState(() => _error = AppLocalizations.of(context).enterCode);
      return;
    }
    await _run(() async {
      _passwordToken = await ref
          .read(authRepositoryProvider)
          .verifyCode(_loginId, _code.text);
      if (mounted) _go(_Step.newPassword);
    });
  }

  Future<void> _savePassword() async {
    final l = AppLocalizations.of(context);
    if (!isAcceptablePassword(_newPassword.text)) {
      setState(() => _error = l.passwordRule);
      return;
    }
    if (_newPassword.text != _confirm.text) {
      setState(() => _error = l.passwordsDiffer);
      return;
    }
    await _run(() => ref
        .read(authControllerProvider.notifier)
        .setPassword(_passwordToken, _newPassword.text));
  }

  Widget _passwordField({
    required String label,
    required TextEditingController controller,
    required bool isNew,
    VoidCallback? onSubmitted,
  }) {
    final l = AppLocalizations.of(context);
    return _Field(
      label: label,
      child: TextField(
        controller: controller,
        enabled: !_busy,
        obscureText: _obscure,
        autofillHints: [
          isNew ? AutofillHints.newPassword : AutofillHints.password,
        ],
        textInputAction:
            onSubmitted == null ? TextInputAction.next : TextInputAction.done,
        onSubmitted: onSubmitted == null ? null : (_) => onSubmitted(),
        decoration: InputDecoration(
          suffixIcon: IconButton(
            tooltip: _obscure ? l.showPassword : l.hidePassword,
            icon: Icon(
              _obscure
                  ? Symbols.visibility_rounded
                  : Symbols.visibility_off_rounded,
            ),
            onPressed: () => setState(() => _obscure = !_obscure),
          ),
        ),
      ),
    );
  }

  /// The ID being signed in, with a way back to change it.
  Widget _idLine() {
    final l = AppLocalizations.of(context);
    return Row(
      children: [
        Expanded(
          child: Text(
            _loginId,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ),
        TextButton(
          onPressed: _busy ? null : () => _go(_Step.id),
          child: Text(l.changeId),
        ),
      ],
    );
  }

  Widget _errorSlot() => Container(
        // Reserved space, so the layout does not jump.
        constraints: const BoxConstraints(minHeight: 40),
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: _error == null
            ? null
            : Semantics(
                liveRegion: true,
                child: Text(
                  _error!,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Theme.of(context).colorScheme.error,
                  ),
                ),
              ),
      );

  /// "Call support" and "WhatsApp support" for an email that is not
  /// registered (AUTH-15).
  Widget _supportButtons() {
    final t = const AuthText();
    final contact = ref.watch(authSupportContactProvider).asData?.value;
    if (contact == null) return const SizedBox.shrink();
    final open = ref.read(linkOpenerProvider);
    final digits = contact.whatsapp.replaceAll(RegExp(r'[^0-9]'), '');
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          OutlinedButton.icon(
            icon: const Icon(Symbols.call_rounded),
            label: Text(t.callSupport),
            onPressed: () => open(Uri(scheme: 'tel', path: contact.helpline)),
          ),
          OutlinedButton.icon(
            icon: const Icon(Symbols.chat_rounded),
            label: Text(t.whatsappSupport),
            onPressed: () => open(Uri.parse('https://wa.me/$digits')),
          ),
        ],
      ),
    );
  }

  /// The consent notice, with the Terms and the Privacy Policy as links
  /// (AUTH-04).
  Widget _termsNotice() {
    final t = const AuthText();
    final base = Theme.of(context)
        .textTheme
        .bodySmall
        ?.copyWith(color: context.brand.mute);
    final link = base?.copyWith(
      decoration: TextDecoration.underline,
      color: Theme.of(context).colorScheme.primary,
    );
    return Text.rich(
      TextSpan(style: base, children: [
        TextSpan(text: t.termsPrefix),
        TextSpan(text: t.termsLink, style: link, recognizer: _termsTap),
        TextSpan(text: t.termsAnd),
        TextSpan(text: t.privacyLink, style: link, recognizer: _privacyTap),
        TextSpan(text: t.termsSuffix),
      ]),
      textAlign: TextAlign.center,
    );
  }

  /// The first screen (AUTH-01): the tagline and two buttons. Both lead to the
  /// email screen.
  List<Widget> _welcomeStep(AppLocalizations l) {
    final t = const AuthText();
    return [
      Text(l.tagline, style: Theme.of(context).textTheme.bodyLarge),
      const SizedBox(height: 32),
      PrimaryButton(label: t.getStarted, onPressed: () => _go(_Step.id)),
      const SizedBox(height: 8),
      Center(
        child: TextButton(
          onPressed: () => _go(_Step.id),
          child: Text(t.alreadyMember),
        ),
      ),
    ];
  }

  List<Widget> _idStep(AppLocalizations l) {
    final config = ref.watch(appConfigProvider);
    final demos = {
      l.demoCustomer: 'customer@priveo.test',
      l.demoCrew: '9000000002',
      l.demoAdmin: 'priveopapa',
    };
    return [
      _Field(
        label: l.loginIdLabel,
        child: TextField(
          controller: _id,
          enabled: !_busy,
          keyboardType: TextInputType.emailAddress,
          autofillHints: const [AutofillHints.username],
          textInputAction: TextInputAction.done,
          onSubmitted: (_) => _continue(),
        ),
      ),
      _errorSlot(),
      if (_notRegistered) _supportButtons(),
      PrimaryButton(label: l.continueButton, busy: _busy, onPressed: _continue),
      const SizedBox(height: 16),
      _termsNotice(),
      if (config.showDemoAccounts) ...[
        const SizedBox(height: 24),
        SectionLabel(l.demoAccounts),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            for (final e in demos.entries)
              OutlinedButton(
                onPressed:
                    _busy ? null : () => setState(() => _id.text = e.value),
                child: Text(e.key),
              ),
          ],
        ),
      ],
    ];
  }

  List<Widget> _passwordStep(AppLocalizations l) => [
        _idLine(),
        const SizedBox(height: 8),
        _passwordField(
          label: l.passwordLabel,
          controller: _password,
          isNew: false,
          onSubmitted: _signIn,
        ),
        _errorSlot(),
        PrimaryButton(label: l.signInButton, busy: _busy, onPressed: _signIn),
        if (_isEmail) ...[
          const SizedBox(height: 8),
          Center(
            child: TextButton(
              onPressed: _busy ? null : _sendCode,
              child: Text(l.forgotPassword),
            ),
          ),
        ],
      ];

  List<Widget> _codeStep(AppLocalizations l) {
    final time = '00:${_resendIn.toString().padLeft(2, '0')}';
    return [
      Text(
        l.codeSentTo(_loginId),
        style: Theme.of(context).textTheme.bodyMedium,
      ),
      const SizedBox(height: 24),
      _CodeBoxes(
        controller: _code,
        enabled: !_busy,
        label: l.codeLabel,
        onChanged: () => setState(() => _error = null),
      ),
      _errorSlot(),
      PrimaryButton(label: l.verifyButton, busy: _busy, onPressed: _verify),
      const SizedBox(height: 8),
      Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          TextButton(
            onPressed: _busy ? null : () => _go(_Step.id),
            child: Text(l.changeEmail),
          ),
          if (_resendIn > 0)
            Text(
              l.resendIn(time),
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: context.brand.mute),
            )
          else
            TextButton(
              onPressed: _busy ? null : _sendCode,
              child: Text(l.resendCode),
            ),
        ],
      ),
    ];
  }

  List<Widget> _newPasswordStep(AppLocalizations l) => [
        Text(l.passwordRule, style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 24),
        _passwordField(
          label: l.newPasswordLabel,
          controller: _newPassword,
          isNew: true,
        ),
        const SizedBox(height: 16),
        _passwordField(
          label: l.confirmPasswordLabel,
          controller: _confirm,
          isNew: true,
          onSubmitted: _savePassword,
        ),
        _errorSlot(),
        PrimaryButton(
          label: l.savePassword,
          busy: _busy,
          onPressed: _savePassword,
        ),
      ];

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final (title, body) = switch (_step) {
      _Step.welcome => (const AuthText().welcomeTitle, _welcomeStep(l)),
      _Step.id => (l.loginTitle, _idStep(l)),
      _Step.password => (l.loginTitle, _passwordStep(l)),
      _Step.code => (l.codeTitle, _codeStep(l)),
      _Step.newPassword => (l.newPasswordTitle, _newPasswordStep(l)),
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
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 24),
                    ...body,
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

/// Six single-digit boxes over one hidden input (AUTH-05). Typing, deleting
/// and pasting all go through the input, so a pasted code fills the boxes.
class _CodeBoxes extends StatefulWidget {
  const _CodeBoxes({
    required this.controller,
    required this.enabled,
    required this.label,
    required this.onChanged,
  });

  final TextEditingController controller;
  final bool enabled;
  final String label;
  final VoidCallback onChanged;

  @override
  State<_CodeBoxes> createState() => _CodeBoxesState();
}

class _CodeBoxesState extends State<_CodeBoxes> {
  final _focus = FocusNode();

  @override
  void initState() {
    super.initState();
    _focus.addListener(_redraw);
    widget.controller.addListener(_redraw);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_redraw);
    _focus.dispose();
    super.dispose();
  }

  void _redraw() => setState(() {});

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final scheme = Theme.of(context).colorScheme;
    final code = widget.controller.text;
    return Stack(
      children: [
        ExcludeSemantics(
          child: Row(
            children: [
              for (var i = 0; i < 6; i++) ...[
                if (i > 0) const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    height: 56,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: scheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(
                        color: _focus.hasFocus && i == code.length.clamp(0, 5)
                            ? b.gold
                            : scheme.outlineVariant,
                        width: 1.5,
                      ),
                    ),
                    child: Text(
                      i < code.length ? code[i] : '',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        // The real input, invisible, covering the boxes so a tap focuses it.
        Positioned.fill(
          child: Semantics(
            label: widget.label,
            child: Opacity(
              opacity: 0,
              child: TextField(
                controller: widget.controller,
                focusNode: _focus,
                enabled: widget.enabled,
                autofocus: true,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(6),
                ],
                showCursor: false,
                enableInteractiveSelection: true,
                onChanged: (_) => widget.onChanged(),
                decoration: const InputDecoration(
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  disabledBorder: InputBorder.none,
                  filled: false,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// A label above its input, with a soft gold glow while the input has focus.
class _Field extends StatefulWidget {
  const _Field({required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  State<_Field> createState() => _FieldState();
}

class _FieldState extends State<_Field> {
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ExcludeSemantics(
          child: Text(
            widget.label,
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: b.mute),
          ),
        ),
        const SizedBox(height: 8),
        Semantics(
          label: widget.label,
          child: Focus(
            canRequestFocus: false,
            skipTraversal: true,
            onFocusChange: (f) => setState(() => _focused = f),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(15),
                boxShadow: [
                  if (_focused)
                    BoxShadow(
                      color: b.gold.withValues(alpha: 0.12),
                      spreadRadius: 4,
                    ),
                ],
              ),
              child: widget.child,
            ),
          ),
        ),
      ],
    );
  }
}
