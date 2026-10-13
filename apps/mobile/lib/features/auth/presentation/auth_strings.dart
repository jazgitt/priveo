/// Text added to the sign-in screens (AUTH-01, AUTH-02, AUTH-04, AUTH-15). The
/// same keys and words are in `lib/l10n/fragments/auth.arb`, which is merged
/// into `app_en.arb` when the slices are joined. A test keeps the two the same.
class AuthText {
  const AuthText();

  static const Map<String, String> all = {
    'auth_welcome_title': 'Welcome to Priveo',
    'auth_get_started': 'Get started',
    'auth_already_member': 'Already a member? Log in',
    'auth_email_invalid': 'Enter a valid email address.',
    'auth_terms_prefix': 'By continuing you accept the ',
    'auth_terms_link': 'Terms',
    'auth_terms_and': ' and the ',
    'auth_privacy_link': 'Privacy Policy',
    'auth_terms_suffix': '.',
    'auth_call_support': 'Call support',
    'auth_whatsapp_support': 'WhatsApp support',
  };

  String get welcomeTitle => all['auth_welcome_title']!;
  String get getStarted => all['auth_get_started']!;
  String get alreadyMember => all['auth_already_member']!;
  String get emailInvalid => all['auth_email_invalid']!;
  String get termsPrefix => all['auth_terms_prefix']!;
  String get termsLink => all['auth_terms_link']!;
  String get termsAnd => all['auth_terms_and']!;
  String get privacyLink => all['auth_privacy_link']!;
  String get termsSuffix => all['auth_terms_suffix']!;
  String get callSupport => all['auth_call_support']!;
  String get whatsappSupport => all['auth_whatsapp_support']!;
}
