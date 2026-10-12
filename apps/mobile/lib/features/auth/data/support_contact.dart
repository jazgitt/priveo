import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';

/// The numbers shown to someone whose email is not registered (AUTH-15). The
/// endpoint needs no sign-in.
class AuthSupportContact {
  const AuthSupportContact({required this.helpline, required this.whatsapp});

  final String helpline;
  final String whatsapp;

  factory AuthSupportContact.fromJson(Map<String, dynamic> json) =>
      AuthSupportContact(
        helpline: json['helpline'] as String,
        whatsapp: json['whatsapp'] as String,
      );
}

/// Read when the "not registered" message is shown. Tests override it.
final authSupportContactProvider =
    FutureProvider.autoDispose<AuthSupportContact?>((ref) async {
  final Dio dio = ref.watch(dioProvider);
  try {
    final r = await dio.get<Map<String, dynamic>>('/v1/auth/support-contact');
    return AuthSupportContact.fromJson(r.data!);
  } on Object {
    // The buttons are an extra: without the numbers only the message shows.
    return null;
  }
});

/// Where the Terms and the Privacy Policy are published. Placeholders until
/// Priveo gives the real addresses.
final termsUri = Uri.parse('https://priveo.in/terms');
final privacyUri = Uri.parse('https://priveo.in/privacy');

/// A format check only: something before and after one `@`, and a dot.
bool isPlausibleEmail(String value) =>
    RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(value);
