// Turns packages/api-contract/openapi.json into lib/core/api/api.g.dart:
// one class per schema and one method per endpoint.
// Run from apps/mobile:  dart run tool/gen_api.dart
//
// It covers what the contract uses today and stops with an error on anything
// else, so a new kind of schema is added here on purpose and not guessed.
import 'dart:convert';
import 'dart:io';

const _skipSchemas = {'HTTPValidationError', 'ValidationError'};
const _reserved = {
  'class', 'default', 'do', 'else', 'enum', 'final', 'for', 'if', 'in', 'is',
  'new', 'null', 'return', 'switch', 'this', 'var', 'void', 'while', 'with',
};

Never _unsupported(String where, Object? what) =>
    throw UnsupportedError('gen_api: $where is not supported yet: $what');

String _camel(String snake) {
  final parts = snake.split('_').where((p) => p.isNotEmpty).toList();
  final name = parts.first +
      parts.skip(1).map((p) => p[0].toUpperCase() + p.substring(1)).join();
  if (_reserved.contains(name)) _unsupported('field or method name', name);
  return name;
}

String _refName(String ref) => ref.split('/').last;

/// A Dart type with the code that reads it from JSON and writes it back.
class _Type {
  _Type(this.dart, this.read, this.write);
  final String dart;
  final String Function(String json) read;
  final String Function(String value) write;
}

_Type _typeOf(Map<String, dynamic> s, String where) {
  if (s[r'$ref'] case final String ref) {
    final name = _refName(ref);
    return _Type(
        name,
        (j) => '$name.fromJson($j as Map<String, dynamic>)',
        (v) => '$v.toJson()');
  }
  // "X or null": the field is always sent, and may be null.
  if (s['anyOf'] case final List<dynamic> options
      when options.length == 2 && options.any((o) => (o as Map)['type'] == 'null')) {
    final inner = _typeOf(
        options.firstWhere((o) => (o as Map)['type'] != 'null')
            as Map<String, dynamic>,
        where);
    return _Type('${inner.dart}?', (j) => '$j == null ? null : ${inner.read(j)}',
        (v) {
      final plain = inner.write(v);
      if (plain == v) return v;
      if (plain.startsWith('$v.')) return '$v?${plain.substring(v.length)}';
      return '$v == null ? null : ${inner.write('$v!')}';
    });
  }
  switch (s['type']) {
    case 'string' when s['format'] == 'date':
      return _Type('DateTime', (j) => 'DateTime.parse($j as String)',
          (v) => '_date($v)');
    case 'string' when s['format'] == null && s['enum'] == null:
      return _Type('String', (j) => '$j as String', (v) => v);
    case 'integer':
      return _Type('int', (j) => '$j as int', (v) => v);
    case 'number':
      return _Type('double', (j) => '($j as num).toDouble()', (v) => v);
    case 'boolean':
      return _Type('bool', (j) => '$j as bool', (v) => v);
    case 'array':
      final item = _typeOf(s['items'] as Map<String, dynamic>, where);
      return _Type(
          'List<${item.dart}>',
          (j) => '[for (final x in $j as List) ${item.read('x')}]',
          (v) => '[for (final x in $v) ${item.write('x')}]');
  }
  _unsupported(where, s);
}

void _writeModel(StringBuffer b, String name, Map<String, dynamic> schema) {
  if (schema['type'] != 'object') _unsupported('schema $name', schema['type']);
  final props = (schema['properties'] as Map<String, dynamic>? ?? {})
      .cast<String, Map<String, dynamic>>();
  final required = ((schema['required'] as List?) ?? const []).toSet();
  final fields = <(String json, String dart, _Type type)>[];
  props.forEach((json, s) {
    if (!required.contains(json)) _unsupported('optional field', '$name.$json');
    fields.add((json, _camel(json), _typeOf(s, '$name.$json')));
  });

  b.writeln('class $name {');
  b.writeln('  const $name({');
  for (final f in fields) {
    b.writeln('    required this.${f.$2},');
  }
  b.writeln('  });\n');
  for (final f in fields) {
    b.writeln('  final ${f.$3.dart} ${f.$2};');
  }
  b.writeln('\n  factory $name.fromJson(Map<String, dynamic> j) => $name(');
  for (final f in fields) {
    b.writeln("        ${f.$2}: ${f.$3.read("j['${f.$1}']")},");
  }
  b.writeln('      );\n');
  b.writeln('  Map<String, dynamic> toJson() => {');
  for (final f in fields) {
    b.writeln("        '${f.$1}': ${f.$3.write(f.$2)},");
  }
  b.writeln('      };');
  b.writeln('}\n');
}

void _writeMethod(
    StringBuffer b, String path, String verb, Map<String, dynamic> op) {
  // FastAPI names an operation "<function>_v1_<path>_<verb>".
  final id = op['operationId'] as String;
  final name = _camel(id.contains('_v1_') ? id.split('_v1_').first : id);

  final params = (op['parameters'] as List? ?? const [])
      .cast<Map<String, dynamic>>();
  for (final p in params) {
    if (p['in'] != 'header' || p['name'] != 'authorization') {
      _unsupported('parameter of $id', p['name']);
    }
  }
  // An endpoint that does not declare the authorization header is called
  // without the bearer token and is never retried after a 401.
  final needsAuth = params.isNotEmpty;

  String? bodyType;
  if (op['requestBody'] case final Map<String, dynamic> body) {
    final s = (body['content'] as Map)['application/json']?['schema'];
    if (s is! Map || s[r'$ref'] == null) _unsupported('request body of $id', s);
    bodyType = _refName(s[r'$ref'] as String);
  }

  final responses = op['responses'] as Map<String, dynamic>;
  final okCode = responses.keys.firstWhere((c) => c.startsWith('2'));
  final okSchema =
      (responses[okCode] as Map)['content']?['application/json']?['schema'];
  String? resultType;
  if (okSchema is Map && okSchema.isNotEmpty) {
    if (okSchema[r'$ref'] == null) _unsupported('response of $id', okSchema);
    resultType = _refName(okSchema[r'$ref'] as String);
  }

  final args = bodyType == null ? '' : '$bodyType body';
  final call = StringBuffer("_dio.$verb<${resultType == null ? 'void' : 'Map<String, dynamic>'}>('$path'");
  if (bodyType != null) call.write(', data: body.toJson()');
  if (!needsAuth) call.write(', options: _noAuth');
  call.write(')');

  if (op['summary'] case final String summary) b.writeln('  /// $summary');
  b.writeln('  Future<${resultType ?? 'void'}> $name($args) async {');
  b.writeln('    try {');
  if (resultType == null) {
    b.writeln('      await $call;');
  } else {
    b.writeln('      final r = await $call;');
    b.writeln('      return $resultType.fromJson(r.data!);');
  }
  b.writeln('    } on DioException catch (e) {');
  b.writeln('      throw ApiFailure.fromDio(e);');
  b.writeln('    }');
  b.writeln('  }\n');
}

void main() {
  final contract = jsonDecode(
          File('../../packages/api-contract/openapi.json').readAsStringSync())
      as Map<String, dynamic>;
  final b = StringBuffer()
    ..writeln('// GENERATED by tool/gen_api.dart from packages/api-contract/openapi.json. Do not edit.')
    ..writeln("import 'package:dio/dio.dart';\n")
    ..writeln("import '../network/api_failure.dart';\n")
    ..writeln('String _date(DateTime d) =>')
    ..writeln("    '\${d.year.toString().padLeft(4, '0')}-'")
    ..writeln("    '\${d.month.toString().padLeft(2, '0')}-'")
    ..writeln("    '\${d.day.toString().padLeft(2, '0')}';\n");

  final schemas = ((contract['components'] as Map)['schemas'] as Map)
      .cast<String, Map<String, dynamic>>();
  for (final name in schemas.keys.toList()..sort()) {
    if (!_skipSchemas.contains(name)) _writeModel(b, name, schemas[name]!);
  }

  b
    ..writeln('/// Every endpoint in the contract. A failed call throws [ApiFailure].')
    ..writeln('class PriveoApi {')
    ..writeln('  PriveoApi(this._dio);\n')
    ..writeln('  final Dio _dio;\n')
    ..writeln("  static final _noAuth = Options(extra: {'noAuth': true});\n");
  (contract['paths'] as Map<String, dynamic>).forEach((path, verbs) {
    (verbs as Map<String, dynamic>).forEach((verb, op) {
      _writeMethod(b, path, verb, op as Map<String, dynamic>);
    });
  });
  final out = b.toString().trimRight();
  File('lib/core/api/api.g.dart')
    ..createSync(recursive: true)
    ..writeAsStringSync('$out\n}\n');
  stdout.writeln('wrote lib/core/api/api.g.dart');
}
