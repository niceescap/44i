import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/rosace_models.dart';

class RosaceApi {
  RosaceApi({http.Client? client, this.locale = 'fr', this.appVersion = '1.0.0+1'})
      : baseUrl = const String.fromEnvironment(
          'API_BASE_URL',
          defaultValue: 'https://44i.webredirect.org',
        ),
        _client = client ?? http.Client();

  static const source = 'android';

  final String baseUrl;
  final String locale;
  final String appVersion;
  final http.Client _client;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'User-Agent': 'LaRosace/$appVersion (Android)',
      };

  Map<String, dynamic> _meta() => {
        'source': source,
        'app_version': appVersion,
        'locale': locale,
      };

  static const _timeout = Duration(seconds: 20);

  Future<Map<String, dynamic>> _decode(http.Response response) {
    Object? value;
    try {
      value = jsonDecode(response.body);
    } catch (_) {
      throw Exception('HTTP ${response.statusCode} depuis $baseUrl');
    }
    if (response.statusCode >= 400) {
      throw Exception(value is Map ? (value['detail'] ?? 'Erreur serveur') : 'Erreur serveur');
    }
    return Future.value(Map<String, dynamic>.from(value as Map));
  }

  Future<RosaceState> createSession({
    required double width,
    required double height,
    required String locale,
  }) async {
    final response = await _client
        .post(
          _uri('/api/v2/sessions'),
          headers: _headers,
          body: jsonEncode({
            'stage_width': width,
            'stage_height': height,
            'locale': locale,
          }),
        )
        .timeout(_timeout);
    return RosaceState.fromJson(await _decode(response));
  }

  Future<Map<String, dynamic>> reveal(String sessionId, int siteId) async {
    final response = await _client.post(
      _uri('/api/v2/sessions/$sessionId/reveal'),
      headers: _headers,
      body: jsonEncode({'site_id': siteId}),
    );
    return _decode(response);
  }

  Future<void> trackVisit({
    required String visitId,
    required String visitorId,
    String? sessionId,
  }) async {
    await _client.post(
      _uri('/api/v2/prospects/visit'),
      headers: _headers,
      body: jsonEncode({
        'visit_id': visitId,
        'visitor_id': visitorId,
        'session_id': sessionId,
        ..._meta(),
      }),
    );
  }

  Future<void> trackEvent({
    required String visitId,
    required String visitorId,
    required String type,
    String? sessionId,
    String? email,
    int? n,
    String? code,
  }) async {
    final body = <String, dynamic>{
      'visit_id': visitId,
      'visitor_id': visitorId,
      'type': type,
      'session_id': sessionId,
      ..._meta(),
    };
    if (email != null) body['email'] = email;
    if (n != null) body['n'] = n;
    if (code != null) body['code'] = code;
    final response = await _client.post(
      _uri('/api/v2/prospects/event'),
      headers: _headers,
      body: jsonEncode(body),
    );
    if (response.statusCode >= 400) {
      throw Exception('Événement refusé (${response.statusCode})');
    }
  }

  Stream<String> interpretStream(String sessionId) =>
      _sse('/api/v2/sessions/$sessionId/interpret/stream', {});

  Stream<String> messageStream(String sessionId, String message) =>
      _sse('/api/v2/sessions/$sessionId/messages/stream', {'message': message});

  Stream<String> _sse(String path, Map<String, dynamic> body) async* {
    final request = http.Request('POST', _uri(path))
      ..headers.addAll(_headers)
      ..body = jsonEncode(body);
    final response = await _client.send(request);
    if (response.statusCode >= 400) {
      throw Exception('Oracle indisponible (${response.statusCode})');
    }
    final buffer = StringBuffer();
    await for (final chunk in response.stream.transform(utf8.decoder)) {
      buffer.write(chunk);
      var raw = buffer.toString();
      final parts = raw.split('\n\n');
      buffer
        ..clear()
        ..write(parts.removeLast());
      for (final part in parts) {
        for (final line in part.split('\n')) {
          if (!line.startsWith('data:')) continue;
          final payload = line.substring(5).trim();
          if (payload.isEmpty) continue;
          final json = jsonDecode(payload);
          if (json is Map && json['error'] != null) {
            throw Exception(json['error']);
          }
          if (json is Map && json['text'] is String) {
            yield json['text'] as String;
          }
        }
      }
    }
  }
}
