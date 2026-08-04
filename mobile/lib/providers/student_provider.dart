import 'package:flutter/foundation.dart';

import '../models/attendance_model.dart';
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
  String? _errorMessage;
  String? _historyError;

  List<AttendanceModel> _attendanceHistory = [];
  List<ClasseScheduleItem> _schedule = [];
  Map<String, dynamic>? _personalStats;
  List<Map<String, dynamic>> _modules = [];
  UserModel? _profile;

  // ─── Getters ──────────────────────────────────────────────────────────────
  bool get isLoading => _isLoading;
  bool get historyLoading => _historyLoading;
  String? get errorMessage => _errorMessage;
  String? get historyError => _historyError;
  List<AttendanceModel> get attendanceHistory => _attendanceHistory;
  List<ClasseScheduleItem> get schedule => _schedule;
  Map<String, dynamic>? get personalStats => _personalStats;
  List<Map<String, dynamic>> get modules => _modules;
  UserModel? get profile => _profile;

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

  Future<void> loadSchedule() async {
    _setLoading(true);
    _clearError();
    try {
      final classes = await _studentService.fetchSchedule();
      _schedule = classes.map(ClasseScheduleItem.fromClasse).toList();
    } catch (e) {
      _setError(e.toString());
    } finally {
      _setLoading(false);
    }
  }

  Future<void> loadModules() async {
    _setLoading(true);
    _clearError();
    try {
      _modules = await _studentService.fetchModules();
    } catch (e) {
      _setError(e.toString());
    } finally {
      _setLoading(false);
    }
  }

  Future<void> loadPersonalStats() async {
    _setLoading(true);
    _clearError();
    try {
      _personalStats = await _studentService.fetchPersonalStats();
    } catch (e) {
      _setError(e.toString());
    } finally {
      _setLoading(false);
    }
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

/// Item d'emploi du temps (basé sur une classe).
class ClasseScheduleItem {
  final int id;
  final String name;
  final String? filiereName;
  final String? moduleName;
  final String? semestreName;
  final String? roomName;
  final String date;

  const ClasseScheduleItem({
    required this.id,
    required this.name,
    this.filiereName,
    this.moduleName,
    this.semestreName,
    this.roomName,
    this.date = '',
  });

  factory ClasseScheduleItem.fromClasse(dynamic classe) {
    return ClasseScheduleItem(
      id: classe.id as int,
      name: classe.name as String? ?? '',
      filiereName: classe.filiereName as String?,
      moduleName: classe.moduleName as String?,
      semestreName: classe.semestreName as String?,
      roomName: classe.roomName as String?,
    );
  }
}
