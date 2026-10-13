import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:dio/dio.dart';

/// Replies with independent OpenAPI fixtures; captures the actual wire request.
/// No network, native plugins or production credentials are used.
class ContractHttp implements HttpClientAdapter {
  final contract = jsonDecode(File('../../packages/api-contract/openapi.json').readAsStringSync()) as Map<String,dynamic>;
  final examples = jsonDecode(File('test/contract/wire_examples.json').readAsStringSync()) as Map<String,dynamic>;
  final requests = <RequestOptions>[];
  final overrides = <String,Object?>{};
  int status = 200;
  Object? schemaValue(Map<String,dynamic> s) {
    if(s.containsKey(r'$ref')) return examples[(s[r'$ref'] as String).split('/').last];
    if(s['type']=='array') return [schemaValue((s['items'] as Map).cast<String,dynamic>())];
    if(s['type']=='object') return <String,dynamic>{};
    return null;
  }
  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? stream, Future<void>? cancel) async {
    requests.add(o);
    if(status>=400) return ResponseBody.fromString(jsonEncode({'code':'conflict','message':'Please review the change.','fields':{'date':'Closed'}}),status,headers:{Headers.contentTypeHeader:[Headers.jsonContentType]});
    Object? body;
    if(overrides.containsKey(o.path)) {body=overrides[o.path];}
    else {
      final paths=(contract['paths'] as Map).cast<String,dynamic>();
      final keys=paths.keys.toList()..sort((a,b)=>a.contains('{')==b.contains('{')?a.compareTo(b):a.contains('{')?1:-1);
      for(final path in keys) {
        final pattern=path.replaceAllMapped(RegExp(r'\{[^}]+\}'),(_)=>'[^/]+');
        if(!RegExp('^$pattern\$').hasMatch(o.path)) continue;
        final op=(paths[path] as Map)[o.method.toLowerCase()] as Map?;
        if(op==null) continue;
        final replies=op['responses'] as Map;
        final ok=replies.keys.firstWhere((k)=>k.toString().startsWith('2'));
        final schema=(replies[ok] as Map)['content']?['application/json']?['schema'];
        body=schema==null?null:schemaValue((schema as Map).cast<String,dynamic>());break;
      }
    }
    return ResponseBody.fromString(jsonEncode(body),200,headers:{Headers.contentTypeHeader:[Headers.jsonContentType]});
  }
  Dio dio()=>Dio(BaseOptions(baseUrl:'https://api.unit.test'))..httpClientAdapter=this;
  @override
  void close({bool force=false}){}
}
