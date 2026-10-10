import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../api/api.g.dart' show LoginResult;

enum Role {
  customer,
  crew,
  admin;

  static Role parse(String v) =>
      Role.values.firstWhere((r) => r.name == v, orElse: () => Role.customer);

  String get homePath => '/$name';
}

class Session {
  const Session({
    required this.role,
    required this.displayName,
    required this.accessToken,
    required this.refreshToken,
  });

  final Role role;
  final String displayName;
  final String accessToken;
  final String refreshToken;

  factory Session.fromLogin(LoginResult r) => Session(
        role: Role.parse(r.role),
        displayName: r.displayName,
        accessToken: r.accessToken,
        refreshToken: r.refreshToken,
      );

  /// Reads the session saved on the phone by [toJson].
  factory Session.fromLoginJson(Map<String, dynamic> j) => Session(
        role: Role.parse(j['role'] as String),
        displayName: j['display_name'] as String,
        accessToken: j['access_token'] as String,
        refreshToken: j['refresh_token'] as String,
      );

  Map<String, dynamic> toJson() => {
        'role': role.name,
        'display_name': displayName,
        'access_token': accessToken,
        'refresh_token': refreshToken,
      };
}

/// Tokens live only in secure storage.
abstract class SessionStore {
  Future<Session?> read();
  Future<void> write(Session session);
  Future<void> clear();
}

class SecureSessionStore implements SessionStore {
  SecureSessionStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'session';
  final FlutterSecureStorage _storage;

  @override
  Future<Session?> read() async {
    try {
      final raw = await _storage.read(key: _key);
      if (raw == null) return null;
      return Session.fromLoginJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> write(Session session) =>
      _storage.write(key: _key, value: jsonEncode(session.toJson()));

  @override
  Future<void> clear() => _storage.delete(key: _key);
}

class MemorySessionStore implements SessionStore {
  Session? _session;

  @override
  Future<Session?> read() async => _session;

  @override
  Future<void> write(Session session) async => _session = session;

  @override
  Future<void> clear() async => _session = null;
}
