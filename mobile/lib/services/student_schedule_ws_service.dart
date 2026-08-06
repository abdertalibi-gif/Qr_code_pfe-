import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../constants/app_constants.dart';
import '../models/student_schedule_model.dart';

/// Callback invoked when a schedule change is received via WebSocket.
typedef ScheduleWsChangeCallback = void Function({
  required String action,
  required StudentScheduleItem? item,
  required int? sessionId,
});

/// Manages a real-time WebSocket connection to the student schedule channel
/// `/ws/schedule/{classe_id}/`.
///
/// When a teacher creates, modifies, or deletes a session for a student's
/// class, the backend broadcasts the change and this service delivers it
/// to listeners so the UI updates immediately — without waiting for the next
/// polling cycle.
/// Manages a real-time WebSocket connection to the student schedule channel
/// `/ws/schedule/{classe_id}/`.
///
/// When a teacher creates, modifies, or deletes a session for a student's
/// class, the backend broadcasts the change and this service delivers it
/// to listeners so the UI updates immediately — without waiting for the next
/// polling cycle.
///
/// The JWT access token (if provided) is appended as a `?token=` query
/// parameter: the backend only accepts students of the matching class.
class StudentScheduleWsService {
  final int classeId;
  final String? token;
  final ScheduleWsChangeCallback onScheduleChange;
  final VoidCallback? onConnected;
  final VoidCallback? onDisconnected;
  final void Function(String)? onError;

  StudentScheduleWsService({
    required this.classeId,
    this.token,
    required this.onScheduleChange,
    this.onConnected,
    this.onDisconnected,
    this.onError,
  });

  WebSocketChannel? _channel;
  bool _connected = false;
  bool _connecting = false;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;

  bool get isConnected => _connected;

  /// Establishes (or re-establishes) the WebSocket connection.
  void connect() {
    if (_connected || _connecting) return;
    _connectInternal();
  }

  void _connectInternal() {
    _connecting = true;
    var url = AppConstants.wsStudentScheduleUri(classeId);
    if (token != null && token!.isNotEmpty) {
      url = '$url?token=${Uri.encodeQueryComponent(token!)}';
    }
    final uri = Uri.parse(url);
    try {
      _channel = WebSocketChannel.connect(uri);
    } catch (e) {
      _connecting = false;
      _connected = false;
      onError?.call('WebSocket connection failed: $e');
      _scheduleReconnect();
      return;
    }

    _channel!.stream.listen(
      _onMessage,
      onDone: _onDone,
      onError: _onError,
    );

    _channel!.sink.done.catchError((_) {});
  }

  void _onMessage(dynamic data) {
    _connecting = false;
    if (!_connected) {
      _connected = true;
      onConnected?.call();
    }
    _reconnectAttempts = 0;

    try {
      final Map<String, dynamic> msg = jsonDecode(data is String ? data : jsonEncode(data));
      if (msg['type'] != 'session_change') return;

      final action = msg['action'] as String? ?? '';
      final itemData = msg['data'] as Map<String, dynamic>?;

      StudentScheduleItem? item;
      int? sessionId;
      if (itemData != null) {
        sessionId = itemData['id'] as int?;
        try {
          item = StudentScheduleItem.fromJson(itemData);
        } catch (_) {
          item = null;
        }
      }

      onScheduleChange(action: action, item: item, sessionId: sessionId);
    } catch (e) {
      if (kDebugMode) print('[StudentScheduleWs] parse error: $e');
    }
  }

  void _onDone() {
    _connected = false;
    _connecting = false;
    onDisconnected?.call();
    _scheduleReconnect();
  }

  void _onError(dynamic error) {
    _connected = false;
    _connecting = false;
    onError?.call(error.toString());
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_reconnectTimer?.isActive ?? false) return;
    _reconnectAttempts++;
    // Exponential backoff: 2s, 4s, 8s, 16s, max 30s
    final delay = Duration(seconds: (2 * _reconnectAttempts).clamp(2, 30));
    _reconnectTimer = Timer(delay, () {
      if (!_connected && !_connecting) {
        _connectInternal();
      }
    });
  }

  /// Call on dispose to release resources.
  void dispose() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    try {
      _channel?.sink.close();
    } catch (_) {}
    _channel = null;
    _connected = false;
    _connecting = false;
  }
}
