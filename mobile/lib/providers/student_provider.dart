import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../constants/app_constants.dart';
import '../models/attendance_model.dart';
import '../models/student_schedule_model.dart';
import '../models/user_model.dart';
import '../services/student_schedule_ws_service.dart';
import '../services/student_service.dart';

enum StudentTab { home, schedule, stats, profile }

class StudentProvider extends ChangeNotifier {
  final StudentService _studentService;

  StudentProvider({StudentService? studentService})
      : _studentService = studentService ?? StudentService();

  // ─── State ────────────────────────────────────────────────────────────────
  StudentTab _currentTab = StudentTab.home;
  StudentTab get currentTab => _currentTab;

  bool _isLoading = false;
  bool _historyLoading = false;
  bool _scheduleLoading = false;
  String? _errorMessage;
  String? _historyError;
  String? _scheduleError;

  List<AttendanceModel> _attendanceHistory = [];
  List<StudentScheduleItem> _schedule = [];
  UserModel? _profile;

  DateTime? _lastScheduleSync;

  Timer? _scheduleTimer;
  StudentScheduleWsService? _wsService;

  // ─── Getters ──────────────────────────────────────────────────────────────
  bool get isLoading => _isLoading;
  bool get historyLoading => _historyLoading;
  bool get scheduleLoading => _scheduleLoading;
  String? get errorMessage => _errorMessage;
  String? get historyError => _historyError;
  String? get scheduleError => _scheduleError;
  List<AttendanceModel> get attendanceHistory => _attendanceHistory;
  List<StudentScheduleItem> get schedule => List.unmodifiable(_schedule);
  UserModel? get profile => _profile;
  DateTime? get lastScheduleSync => _lastScheduleSync;
  bool get wsConnected => _wsService?.isConnected ?? false;

  // ─── Actions ──────────────────────────────────────────────────────────────

  void setTab(StudentTab tab) {
    if (_currentTab != tab) {
      _currentTab = tab;
      notifyListeners();
    }
  }

  Future<void> loadHistory({bool refresh = false}) async {
    if (_historyLoading) return;
    _historyLoading = true;
    _historyError = null;
    notifyListeners();
    try {
      _attendanceHistory = await _studentService.fetchMyAttendance();
    } catch (e) {
      _historyError = e.toString();
    } finally {
      _historyLoading = false;
      notifyListeners();
    }
  }

  /// Emploi du temps dynamique de l'étudiant.
  ///
  /// [silent] évite le spinner plein écran lors des rafraîchissements
  /// automatiques (timer / retour au premier plan).
  Future<void> loadSchedule({bool silent = false}) async {
    if (_scheduleLoading) return;
    if (!silent) {
      _scheduleLoading = true;
      _scheduleError = null;
      notifyListeners();
    }
    try {
      _schedule = await _studentService.fetchMySchedule();
      _lastScheduleSync = DateTime.now();
      if (_scheduleError != null) {
        _scheduleError = null;
        notifyListeners();
      }
      // Reconnect WebSocket with the latest class ID (in case it changed).
      await _connectWebSocket();
    } catch (e) {
      _scheduleError = e.toString();
      notifyListeners();
    } finally {
      if (!silent) {
        _scheduleLoading = false;
        notifyListeners();
      }
    }
  }

  /// Connects (or reconnects) the student schedule WebSocket for real-time
  /// updates. Called after each schedule fetch so the class ID is fresh.
  Future<void> _connectWebSocket() async {
    final classeId = profile?.studentProfile?.classeId;
    if (classeId == null) return;

    // Reuse existing connection if already connected for the same class.
    if (_wsService?.isConnected ?? false) return;
    _wsService?.dispose();

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(AppConstants.accessTokenKey);

    _wsService = StudentScheduleWsService(
      classeId: classeId,
      token: token,
      onScheduleChange: _handleWsChange,
      onConnected: () => notifyListeners(),
      onDisconnected: () => notifyListeners(),
    );
    _wsService!.connect();
  }

  /// Handles a real-time schedule change received via WebSocket.
  void _handleWsChange({
    required String action,
    required StudentScheduleItem? item,
    required int? sessionId,
  }) {
    // Never merge a session belonging to another class, even if it were
    // received on this channel.
    final studentClasse = profile?.studentProfile?.classeId;
    if (item?.classe != null && studentClasse != null) {
      if (item!.classe != studentClasse) return;
    }
    if (action == 'deleted' && sessionId != null) {
      _schedule.removeWhere((s) => s.id == sessionId);
    } else if (item != null && (action == 'created' || action == 'updated')) {
      final idx = _schedule.indexWhere((s) => s.id == item.id);
      if (idx >= 0) {
        _schedule[idx] = item;
      } else {
        _schedule.add(item);
      }
      _schedule.sort((a, b) {
        if (a.date != b.date) return a.date.compareTo(b.date);
        return a.startMinutes.compareTo(b.startMinutes);
      });
    }
    _lastScheduleSync = DateTime.now();
    notifyListeners();
  }

  /// Démarre la synchronisation périodique de l'emploi du temps.
  void startScheduleAutoRefresh({Duration interval = const Duration(seconds: 30)}) {
    _scheduleTimer?.cancel();
    _scheduleTimer = Timer.periodic(interval, (_) {
      if (_currentTab == StudentTab.schedule || _currentTab == StudentTab.home) {
        loadSchedule(silent: true);
      }
    });
  }

  /// Arrête la synchronisation périodique.
  void stopScheduleAutoRefresh() {
    _scheduleTimer?.cancel();
    _scheduleTimer = null;
  }

  /// Rafraîchit l'emploi du temps lors du retour au premier plan.
  void refreshOnForeground() {
    loadSchedule(silent: true);
  }

  /// Sets the student profile from the AuthProvider (avoids a redundant
  /// API call — the user is already fetched at login).
  void setUserProfile(UserModel user) {
    _profile = user;
    notifyListeners();
  }

  Future<void> loadProfile() async {
    _setLoading(true);
    _clearError();
    try {
      final raw = await _studentService.fetchStudentProfile();
      _profile = UserModel.fromJson(raw);
    } catch (e) {
      _setError(e.toString());
    } finally {
      _setLoading(false);
    }
  }

  @override
  void dispose() {
    _scheduleTimer?.cancel();
    _wsService?.dispose();
    _wsService = null;
    super.dispose();
  }

  // ─── Private helpers ─────────────────────────────────────────────────────

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void _setError(String message) {
    _errorMessage = message;
    notifyListeners();
  }

  void _clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}
