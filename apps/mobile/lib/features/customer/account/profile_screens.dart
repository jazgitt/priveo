import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_failure.dart';
import '../../../core/ui/theme.dart';
import '../../../core/ui/widgets.dart';
import '../cust_ui.dart';
import 'account_data.dart';
import 'account_strings.dart';

final _name = RegExp(r"^[A-Za-z][A-Za-z .'-]{0,79}$"); // ONB-02
final _emailShape = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

void openEditProfile(BuildContext context) => Navigator.of(
  context,
).push(MaterialPageRoute<void>(builder: (_) => const EditProfileScreen()));

void openChangePassword(BuildContext context) => Navigator.of(
  context,
).push(MaterialPageRoute<void>(builder: (_) => const ChangePasswordScreen()));

String _failureText(Object e) =>
    e is ApiFailure && e.message != null ? e.message! : AccountStrings.uploadFailed;

class _ErrorLine extends StatelessWidget {
  const _ErrorLine(this.text);

  final String? text;

  @override
  Widget build(BuildContext context) => text == null
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Semantics(
            liveRegion: true,
            child: Text(
              text!,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.error,
              ),
            ),
          ),
        );
}

/// Edit profile (ACC-06): names and mobile number. The email changes through
/// its own code step (ACC-08).
class EditProfileScreen extends ConsumerWidget {
  const EditProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => CustPage(
    title: AccountStrings.editProfile,
    body: AsyncBody<ProfileDto>(
      value: ref.watch(profileProvider),
      onRetry: () => ref.invalidate(profileProvider),
      builder: (p) => _EditProfileForm(p),
    ),
  );
}

class _EditProfileForm extends ConsumerStatefulWidget {
  const _EditProfileForm(this.profile);

  final ProfileDto profile;

  @override
  ConsumerState<_EditProfileForm> createState() => _EditProfileFormState();
}

class _EditProfileFormState extends ConsumerState<_EditProfileForm> {
  late final _first = TextEditingController(text: widget.profile.firstName);
  late final _last = TextEditingController(text: widget.profile.lastName);
  late final _mobile = TextEditingController(text: widget.profile.mobile);
  final _errors = <String, String>{};
  String? _failure;
  bool _busy = false;

  @override
  void dispose() {
    _first.dispose();
    _last.dispose();
    _mobile.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final errors = <String, String>{};
    if (!_name.hasMatch(_first.text.trim())) {
      errors['first'] = AccountStrings.enterFirstName;
    }
    if (!_name.hasMatch(_last.text.trim())) {
      errors['last'] = AccountStrings.enterLastName;
    }
    final mobile = _mobile.text.trim();
    if (mobile != widget.profile.mobile &&
        !RegExp(r'^\d{10}$').hasMatch(mobile)) {
      errors['mobile'] = AccountStrings.enterMobile;
    }
    setState(() {
      _errors
        ..clear()
        ..addAll(errors);
      _failure = null;
    });
    if (errors.isNotEmpty) return;
    setState(() => _busy = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref
          .read(accountRepositoryProvider)
          .editProfile(
            firstName: _first.text.trim(),
            lastName: _last.text.trim(),
            mobile: mobile,
          );
      ref.invalidate(profileProvider);
      messenger.showSnackBar(
        const SnackBar(content: Text(AccountStrings.profileSaved)),
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _failure = _failureText(e);
          _busy = false;
        });
      }
    }
  }

  Widget _field(String key, String label, TextEditingController c,
      {TextInputType? keyboard, TextCapitalization cap = TextCapitalization.none}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: c,
            enabled: !_busy,
            keyboardType: keyboard,
            textCapitalization: cap,
            decoration: InputDecoration(labelText: label),
          ),
          _ErrorLine(_errors[key]),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    final text = Theme.of(context).textTheme;
    final p = widget.profile;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _field('first', AccountStrings.firstName, _first,
            cap: TextCapitalization.words),
        _field('last', AccountStrings.lastName, _last,
            cap: TextCapitalization.words),
        _field('mobile', AccountStrings.mobile, _mobile,
            keyboard: TextInputType.phone),
        Card(
          child: ListTile(
            title: const Text(AccountStrings.email),
            subtitle: Text(
              p.pendingEmail == null
                  ? p.email
                  : '${p.email}\n${AccountStrings.pendingEmail} ${p.pendingEmail}',
            ),
            isThreeLine: p.pendingEmail != null,
            trailing: TextButton(
              onPressed: _busy
                  ? null
                  : () async {
                      await Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => const ChangeEmailScreen(),
                        ),
                      );
                      ref.invalidate(profileProvider);
                    },
              child: const Text(AccountStrings.changeEmail),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(p.society, style: text.bodySmall?.copyWith(color: b.mute)),
        _ErrorLine(_failure),
        const SizedBox(height: 20),
        PrimaryButton(
          label: AccountStrings.save,
          busy: _busy,
          onPressed: _save,
        ),
      ],
    );
  }
}

/// Change email (ACC-08): a code goes to the new email. The old email stays in
/// use until the code is entered.
class ChangeEmailScreen extends ConsumerStatefulWidget {
  const ChangeEmailScreen({super.key});

  @override
  ConsumerState<ChangeEmailScreen> createState() => _ChangeEmailScreenState();
}

class _ChangeEmailScreenState extends ConsumerState<ChangeEmailScreen> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  bool _sent = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final email = _email.text.trim();
    if (!_emailShape.hasMatch(email)) {
      setState(() => _error = AccountStrings.enterEmail);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(accountRepositoryProvider).startEmailChange(email);
      if (mounted) setState(() => _sent = true);
    } catch (e) {
      if (mounted) setState(() => _error = _failureText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(accountRepositoryProvider).verifyEmail(_code.text.trim());
      ref.invalidate(profileProvider);
      messenger.showSnackBar(
        const SnackBar(content: Text(AccountStrings.emailChanged)),
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = _failureText(e);
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final b = context.brand;
    return CustPage(
      title: AccountStrings.changeEmail,
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(
            controller: _email,
            enabled: !_sent && !_busy,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(labelText: AccountStrings.newEmail),
          ),
          if (_sent) ...[
            const SizedBox(height: 12),
            Text(
              AccountStrings.emailCodeSent,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: b.mute),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _code,
              enabled: !_busy,
              keyboardType: TextInputType.number,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(6),
              ],
              decoration: const InputDecoration(labelText: AccountStrings.code),
            ),
          ],
          _ErrorLine(_error),
          const SizedBox(height: 20),
          PrimaryButton(
            label: _sent ? AccountStrings.verify : AccountStrings.sendCode,
            busy: _busy,
            onPressed: _sent ? _verify : _send,
          ),
        ],
      ),
    );
  }
}

/// Change password. The other devices are signed out by the API.
class ChangePasswordScreen extends ConsumerStatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  ConsumerState<ChangePasswordScreen> createState() =>
      _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends ConsumerState<ChangePasswordScreen> {
  final _current = TextEditingController();
  final _next = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _current.dispose();
    _next.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final pw = _next.text;
    if (pw.length < 8 ||
        !RegExp(r'[A-Za-z]').hasMatch(pw) ||
        !RegExp(r'\d').hasMatch(pw)) {
      setState(() => _error = AccountStrings.passwordRule);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref
          .read(accountRepositoryProvider)
          .changePassword(current: _current.text, next: pw);
      messenger.showSnackBar(
        const SnackBar(content: Text(AccountStrings.passwordChanged)),
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = _failureText(e);
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => CustPage(
    title: AccountStrings.changePassword,
    body: ListView(
      padding: const EdgeInsets.all(20),
      children: [
        TextField(
          controller: _current,
          obscureText: true,
          enabled: !_busy,
          decoration: const InputDecoration(
            labelText: AccountStrings.currentPassword,
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _next,
          obscureText: true,
          enabled: !_busy,
          decoration: const InputDecoration(
            labelText: AccountStrings.newPassword,
            helperText: AccountStrings.passwordRule,
          ),
        ),
        _ErrorLine(_error),
        const SizedBox(height: 20),
        PrimaryButton(
          label: AccountStrings.save,
          busy: _busy,
          onPressed: _save,
        ),
      ],
    ),
  );
}
