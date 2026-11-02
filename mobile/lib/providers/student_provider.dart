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
  int? _selectedClassId;

  DateTime? _lastScheduleSync;

  Timer? _scheduleTimer;
  StudentScheduleWsService? _wsService;
  int? _wsClasseId;

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
  int? get selectedClassId => _selectedClassId;
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
  Future<void> loadSchedule({bool silent = false, int? classId}) async {
    if (_scheduleLoading) return;
    if (!silent) {
      _scheduleLoading = true;
      _scheduleError = null;
      notifyListeners();
    }
    try {
      _schedule = await _studentService.fetchMySchedule(classId: classId ?? _selectedClassId);
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
  /// updates. Called after each schedule/profile fetch so the class ID is
  /// always fresh.
  ///
  /// [force] forces a reconnection even if the service is already connected
  /// (used when the student has been reassigned to another class).
  Future<void> _connectWebSocket({bool force = false}) async {
    final classeId = profile?.studentProfile?.classeId;
    if (classeId == null) {
      _wsService?.dispose();
      _wsService = null;
      _wsClasseId = null;
      return;
    }

    // Reuse the existing connection only if it targets the same class.
    if (!force && _wsService != null && _wsClasseId == classeId) return;
    _wsService?.dispose();

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(AppConstants.accessTokenKey);

    _wsClasseId = classeId;
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

  /// Démarre la synchronisation périodique du profil et de l'emploi du temps.
  ///
  /// Le profil est rafraîchi à chaque cycle (même sur l'onglet Profil) afin
  /// qu'une nouvelle affectation de classe soit visible sans redémarrage.
  void startScheduleAutoRefresh({Duration interval = const Duration(seconds: 30)}) {
    _scheduleTimer?.cancel();
    _scheduleTimer = Timer.periodic(interval, (_) async {
      await refreshProfile(silent: true);
      if (_currentTab == StudentTab.schedule || _currentTab == StudentTab.home) {
        await loadSchedule(silent: true, classId: _selectedClassId);
      }
    });
  }

  /// Arrête la synchronisation périodique.
  void stopScheduleAutoRefresh() {
    _scheduleTimer?.cancel();
    _scheduleTimer = null;
  }

  /// Rafraîchit le profil et l'emploi du temps au retour au premier plan.
  Future<void> refreshOnForeground() async {
    await refreshProfile(silent: true);
    await loadSchedule(silent: true, classId: _selectedClassId);
  }

  /// Recharge le profil depuis `/auth/me/` sans recharger l'écran.
  ///
  /// Si la classe de l'étudiant a changé, l'ancien emploi du temps est vidé,
  /// le WebSocket est reconnecté sur la nouvelle classe et les séances sont
  /// rechargées immédiatement.
  Future<bool> refreshProfile({bool silent = false}) async {
    final previousClasseId = _profile?.studentProfile?.classeId;
    try {
      final raw = await _studentService.fetchStudentProfile();
      _profile = UserModel.fromJson(raw);

      final classeChanged =
          previousClasseId != _profile?.studentProfile?.classeId;
      if (classeChanged) {
        _schedule.clear();
        _lastScheduleSync = null;
        await _connectWebSocket(force: true);
        await loadSchedule(silent: true, classId: _selectedClassId);
      }

      notifyListeners();
      return true;
    } catch (e) {
      if (!silent) {
        _errorMessage = e.toString();
        notifyListeners();
      }
      return false;
    }
  }

  /// Sélectionne/désélectionne une classe pour filtrer l'emploi du temps.
  /// Passer `null` affiche toutes les classes de l'étudiant.
  void selectClass(int? classId) {
    _selectedClassId = classId;
    notifyListeners();
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
      await refreshProfile();
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
    _wsClasseId = null;
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
