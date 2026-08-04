import 'package:flutter/foundation.dart';

import '../models/classe_model.dart';
import '../models/session_model.dart';
import '../services/teacher_service.dart';

enum TeacherTab {
  dashboard,
  sessions,
  attendance,
  statistics,
  profile,
}

class TeacherProvider extends ChangeNotifier {
  final TeacherService _teacherService;

  TeacherProvider({TeacherService? teacherService})
      : _teacherService = teacherService ?? TeacherService();

  // ─── State ────────────────────────────────────────────────────────────────

  TeacherTab _currentTab = TeacherTab.dashboard;
  TeacherTab get currentTab => _currentTab;

  // Dashboard data
  bool _isLoading = false;
  String? _errorMessage;
  List<SessionModel> _sessions = [];
  List<SessionAttendance> _liveAttendance = [];
  GlobalStats? _globalStats;
  ClasseModel? _selectedClasse;

  // Sessions UI state
  bool _sessionsLoading = false;
  String? _sessionsError;
  List<ClasseModel> _classes = [];
  List<SessionModel> _allSessions = [];

  // Session detail UI state
  bool _sessionDetailLoading = false;
  String? _sessionDetailError;
  SessionModel? _selectedSession;
  List<SessionAttendance> _sessionAttendees = [];
  SessionStats? _sessionStats;
  List<SuspiciousAttempt> _suspiciousAttempts = [];

  // QR generation UI state
  bool _qrLoading = false;
  String? _qrError;
  SessionQrPayload? _qrPayload;

  // ─── Getters ──────────────────────────────────────────────────────────────

  bool get isLoading => _isLoading;
  bool get sessionsLoading => _sessionsLoading;
  bool get sessionDetailLoading => _sessionDetailLoading;
  bool get qrLoading => _qrLoading;
  String? get errorMessage => _errorMessage;
  String? get sessionsError => _sessionsError;
  String? get sessionDetailError => _sessionDetailError;
  String? get qrError => _qrError;

  List<SessionModel> get sessions => _sessions;
  List<SessionAttendance> get liveAttendance => _liveAttendance;
  GlobalStats? get globalStats => _globalStats;
  ClasseModel? get selectedClasse => _selectedClasse;
  List<ClasseModel> get classes => _classes;
  List<SessionModel> get allSessions => _allSessions;
  SessionModel? get selectedSession => _selectedSession;
  List<SessionAttendance> get sessionAttendees => _sessionAttendees;
  SessionStats? get sessionStats => _sessionStats;
  List<SuspiciousAttempt> get suspiciousAttempts => _suspiciousAttempts;
  SessionQrPayload? get qrPayload => _qrPayload;

  bool get isDashboard => _currentTab == TeacherTab.dashboard;
  bool get isSessions => _currentTab == TeacherTab.sessions;
  bool get isAttendance => _currentTab == TeacherTab.attendance;
  bool get isStatistics => _currentTab == TeacherTab.statistics;
  bool get isProfile => _currentTab == TeacherTab.profile;

  // ─── Actions ──────────────────────────────────────────────────────────────

  void setTab(TeacherTab tab) {
    if (_currentTab != tab) {
      _currentTab = tab;
      notifyListeners();
    }
  }

  Future<void> loadDashboard() async {
    _setLoading(true);
    _clearError();
    try {
      final classes = await _teacherService.fetchClasses();
      _classes = classes;

      // Charger les sessions actives pour le dashboard
      final allSessions = await _teacherService.fetchSessions();
      _allSessions = allSessions;

      // Sessions des 24 dernières heures seulement
      final now = DateTime.now();
      _sessions = allSessions.where((s) {
        final sessionDateTime = s.dateTime;
        if (sessionDateTime == null) return false;
        final diff = now.difference(sessionDateTime).inHours;
        return diff <= 24 && diff >= -48;
      }).toList();

      final live = await _teacherService.fetchLiveAttendance();
      _liveAttendance = live;

      final stats = await _teacherService.fetchGlobalStats(period: 30);
      _globalStats = stats;
    } catch (e) {
      _setError(e.toString());
    } finally {
      _setLoading(false);
    }
  }

  Future<void> loadSessions() async {
    _setSessionsLoading(true);
    _clearSessionsError();
    try {
      final classes = await _teacherService.fetchClasses();
      _classes = classes;

      final allSessions = await _teacherService.fetchSessions();
      _allSessions = allSessions;

      _selectedClasse = classes.isNotEmpty ? classes.first : null;
      if (_selectedClasse != null) {
        _sessions = allSessions
            .where((s) => s.classe == _selectedClasse!.id)
            .toList();
      }
    } catch (e) {
      _setSessionsError(e.toString());
    } finally {
      _setSessionsLoading(false);
    }
  }

  /// Recharge classes + séances en conservant la classe sélectionnée.
  Future<void> refreshSessions() async {
    _setSessionsLoading(true);
    try {
      _classes = await _teacherService.fetchClasses();
      final all = await _teacherService.fetchSessions();
      _allSessions = all;
      final current = _selectedClasse;
      _selectedClasse = (current != null &&
              _classes.any((c) => c.id == current.id))
          ? current
          : (_classes.isNotEmpty ? _classes.first : null);
      _sessions = _selectedClasse == null
          ? all
          : all.where((s) => s.classe == _selectedClasse!.id).toList();
    } catch (e) {
      _setSessionsError(e.toString());
    } finally {
      _setSessionsLoading(false);
    }
  }

  /// Rafraîchit uniquement les données "live" (présences + stats globales).
  Future<void> refreshDashboardLive() async {
    try {
      _liveAttendance = await _teacherService.fetchLiveAttendance();
      _globalStats = await _teacherService.fetchGlobalStats(period: 30);
      notifyListeners();
    } catch (_) {
      // Silencieux : le prochain cycle réessaiera.
    }
  }

  /// Charge les statistiques globales pour une période donnée.
  Future<void> loadGlobalStats(int period) async {
    _setLoading(true);
    _clearError();
    try {
      _globalStats = await _teacherService.fetchGlobalStats(period: period);
    } catch (e) {
      _setError(e.toString());
    } finally {
      _setLoading(false);
    }
  }

  void selectClasse(ClasseModel classe) {
    if (_selectedClasse?.id == classe.id) return;
    _selectedClasse = classe;
    _loadSessionsForSelectedClasse();
  }

  Future<void> _loadSessionsForSelectedClasse() async {
    if (_selectedClasse == null) {
      _sessions = [];
      return;
    }
    _setSessionsLoading(true);
    try {
      final sessions = await _teacherService.fetchSessions(
        classeId: _selectedClasse!.id,
      );
      _sessions = sessions;
    } catch (e) {
      _setSessionsError(e.toString());
    } finally {
      _setSessionsLoading(false);
    }
  }

  Future<void> loadSessionDetail(int sessionId) async {
    _setSessionDetailLoading(true);
    _clearSessionDetailError();
    try {
      _selectedSession = await _teacherService.fetchSession(sessionId);

      final attendees = await _teacherService.fetchSessionAttendance(sessionId);
      _sessionAttendees = attendees;

      final stats = await _teacherService.fetchSessionStats(sessionId);
      _sessionStats = stats;

      final suspicious = await _teacherService.fetchSuspiciousAttempts(sessionId);
      _suspiciousAttempts = suspicious;
    } catch (e) {
      _setSessionDetailError(e.toString());
    } finally {
      _setSessionDetailLoading(false);
    }
  }

  Future<void> generateQr(
    int sessionId, {
    required int expiryMinutes,
    required int attendanceRadiusMeters,
    double? latitude,
    double? longitude,
  }) async {
    _setQrLoading(true);
    _clearQrError();
    try {
      _qrPayload = await _teacherService.generateQr(
        sessionId,
        expiryMinutes: expiryMinutes,
        attendanceRadiusMeters: attendanceRadiusMeters,
        latitude: latitude,
        longitude: longitude,
      );
    } catch (e) {
      _setQrError(e.toString());
    } finally {
      _setQrLoading(false);
    }
  }

  Future<void> fetchCurrentQr(int sessionId) async {
    _setQrLoading(true);
    _clearQrError();
    try {
      final payload = await _teacherService.fetchCurrentQr(sessionId);
      _qrPayload = payload;
    } catch (e) {
      _setQrError(e.toString());
    } finally {
      _setQrLoading(false);
    }
  }

  Future<void> closeSession(int sessionId) async {
    _setQrLoading(true);
    _clearQrError();
    try {
      await _teacherService.closeSession(sessionId);
      // Recharger la session
      await loadSessionDetail(sessionId);
    } catch (e) {
      _setQrError(e.toString());
    } finally {
      _setQrLoading(false);
    }
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

  void _setSessionsLoading(bool loading) {
    _sessionsLoading = loading;
    notifyListeners();
  }

  void _setSessionsError(String message) {
    _sessionsError = message;
    notifyListeners();
  }

  void _clearSessionsError() {
    _sessionsError = null;
    notifyListeners();
  }

  void _setSessionDetailLoading(bool loading) {
    _sessionDetailLoading = loading;
    notifyListeners();
  }

  void _setSessionDetailError(String message) {
    _sessionDetailError = message;
    notifyListeners();
  }

  void _clearSessionDetailError() {
    _sessionDetailError = null;
    notifyListeners();
  }

  void _setQrLoading(bool loading) {
    _qrLoading = loading;
    notifyListeners();
  }

  void _setQrError(String message) {
    _qrError = message;
    notifyListeners();
  }

  void _clearQrError() {
    _qrError = null;
    notifyListeners();
  }
}
