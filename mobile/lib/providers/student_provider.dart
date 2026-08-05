import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/attendance_model.dart';
import '../models/student_schedule_model.dart';
import '../models/user_model.dart';
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

  // ─── Getters ──────────────────────────────────────────────────────────────
  bool get isLoading => _isLoading;
  bool get historyLoading => _historyLoading;
  bool get scheduleLoading => _scheduleLoading;
  String? get errorMessage => _errorMessage;
  String? get historyError => _historyError;
  String? get scheduleError => _scheduleError;
  List<AttendanceModel> get attendanceHistory => _attendanceHistory;
  List<StudentScheduleItem> get schedule => _schedule;
  UserModel? get profile => _profile;
  DateTime? get lastScheduleSync => _lastScheduleSync;

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
    } catch (e) {
      _scheduleError = e.toString();
    } finally {
      if (!silent) {
        _scheduleLoading = false;
        notifyListeners();
      }
    }
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
