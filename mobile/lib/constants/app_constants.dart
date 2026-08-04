import 'package:flutter/foundation.dart';

class AppConstants {
  // ─── API Base URL ─────────────────────────────────────────────────────────
  // Production (Render, Railway, etc.) — set this when the API is not on your PC:
  //   flutter run --dart-define=API_BASE_URL=https://YOUR-SERVICE.onrender.com/api/v1
  // Physical device on the same Wi‑Fi as your PC (default below).
  // Android emulator only: use host loopback alias:
  //   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
  // Different PC IP:
  //   flutter run --dart-define=DEV_HOST=192.168.x.x
  //   or --dart-define=API_BASE_URL=http://192.168.x.x:8000/api/v1
  static const String _apiBaseUrlOverride = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  /// LAN IP of the machine running Django (must match ALLOWED_HOSTS in backend).
  static const String devHost = String.fromEnvironment(
    'DEV_HOST',
    defaultValue: '192.168.1.15',
  );

  static const int apiPort = 8000;

  static String get baseUrl {
    final override = _apiBaseUrlOverride.trim();
    if (override.isNotEmpty) {
      return override.endsWith('/') ? override.substring(0, override.length - 1) : override;
    }
    if (kIsWeb) return 'http://localhost:$apiPort/api/v1';
    // Real phones cannot use localhost or 10.0.2.2 — use your PC's LAN IP.
    return 'http://$devHost:$apiPort/api/v1';
  }

  /// WebSocket root (no trailing slash) derived from [baseUrl].
  /// The Django channels routes live under `/ws/...` (not `/api/v1/...`),
  /// so the `/api/v1` prefix is stripped from the base URL.
  static String get wsServerRoot {
    final base = _stripApiPrefix(baseUrl);
    if (base.startsWith('https://')) {
      return 'wss://${base.substring(8)}';
    }
    if (base.startsWith('http://')) {
      return 'ws://${base.substring(7)}';
    }
    return base;
  }

  static String _stripApiPrefix(String url) {
    if (url.endsWith('/api/v1')) return url.substring(0, url.length - 7);
    if (url.endsWith('/api/v1/')) return url.substring(0, url.length - 8);
    return url;
  }

  // ─── WebSocket paths ──────────────────────────────────────────────────────
  static String wsTeacherLiveUri(int teacherId) => '$wsServerRoot/ws/attendance/live/teacher/$teacherId/';
  static String wsSessionUri(int sessionId) => '$wsServerRoot/ws/attendance/$sessionId/';

  // ─── Endpoints ────────────────────────────────────────────────────────────
  static const String loginEndpoint = '/auth/login/';
  static const String refreshEndpoint = '/auth/refresh/';
  static const String meEndpoint = '/auth/me/';
  static const String validateAttendanceEndpoint = '/attendance/validate/';
  static const String validateAppAttendanceEndpoint = '/attendance/validate/app/';
  static const String myAttendanceEndpoint = '/attendance/my/';
  static const String appDeepLinkScheme = 'presenceqr';

  // ─── Teacher / curriculum endpoints ──────────────────────────────────────
  static const String classesEndpoint = '/classes/';
  static const String sessionsEndpoint = '/sessions/';
  static const String sessionAvailableLocationsEndpoint =
      '/sessions/available-locations/';
  static const String teachersEndpoint = '/teachers/';
  static const String attendanceEndpoint = '/attendance/';
  static const String curriculumEndpoint = '/curriculum/';
  static const String curriculumModulesEndpoint = '/curriculum/modules/';
  static const String curriculumNiveauxEndpoint = '/curriculum/niveaux/';
  static const String statisticsEndpoint = '/statistics/';
  static const String blocksEndpoint = '/blocks/';
  static const String amphitheatersEndpoint = '/amphitheaters/';
  static const String studentsEndpoint = '/students/';
  static const String exportWizardEndpoint = '/attendance/export-wizard/';

  static String sessionDetailEndpoint(int id) => '/sessions/$id/';
  static String sessionGenerateQrEndpoint(int id) => '/sessions/$id/generate-qr/';
  static String sessionCurrentQrEndpoint(int id) => '/sessions/$id/current-qr/';
  static String sessionCloseEndpoint(int id) => '/sessions/$id/close/';
  static String sessionAttendanceEndpoint(int id) => '/attendance/session/$id/';
  static String sessionStatsEndpoint(int id) => '/attendance/session/$id/stats/';
  static String sessionSuspiciousEndpoint(int id) =>
      '/attendance/session/$id/suspicious/';
  static String sessionExportEndpoint(int id) =>
      '/attendance/session/$id/export/';
  static String sessionReportEndpoint(int id) =>
      '/attendance/session/$id/report/';

  // ─── SharedPreferences keys ───────────────────────────────────────────────
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userDataKey = 'user_data';
  static const String themeKey = 'theme_mode';

  // ─── HTTP timeouts (ms) ───────────────────────────────────────────────────
  // Render free tier can cold-start 30–60s; local Wi‑Fi may be slow too.
  static const int connectTimeout = 60000;
  static const int receiveTimeout = 60000;

  // ─── Named routes ─────────────────────────────────────────────────────────
  static const String routeSplash = '/';
  static const String routeLogin = '/login';
  static const String routeHome = '/home';
  static const String routeScanner = '/scanner';
  static const String routeValidation = '/validation';
  static const String routeSuccess = '/success';
  static const String routeError = '/error';

  // ─── Teacher routes ───────────────────────────────────────────────────────
  static const String routeTeacherHome = '/teacher/home';
  static const String routeSessions = '/teacher/sessions';
  static const String routeSessionForm = '/teacher/session-form';
  static const String routeSessionDetail = '/teacher/session-detail';
  static const String routeGenerateQr = '/teacher/generate-qr';
  static const String routeTeacherProfile = '/teacher/profile';
  static const String routeTeacherDashboard = '/teacher/dashboard';
  static const String routeExport = '/teacher/export';

  // ─── Student routes ───────────────────────────────────────────────────────
  static const String routeStudentProfile = '/student/profile';
  static const String routeStudentSchedule = '/student/schedule';
  static const String routeStudentStats = '/student/stats';
  static const String routeStudentModules = '/student/modules';
  static const String routeStudentAbsences = '/student/absences';
  static const String routeStudentQr = '/student/qr';
  static const String routeStudentHome = '/student/home';

  // ─── Other ────────────────────────────────────────────────────────────────
  static const String routeRoleNotSupported = '/role-not-supported';

  // ─── Misc ─────────────────────────────────────────────────────────────────
  static const String appName = 'PrésenceQR';
  static const String appVersion = '1.0.0';
}
