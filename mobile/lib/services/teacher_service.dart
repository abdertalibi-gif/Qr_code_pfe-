import 'dart:typed_data';

import '../constants/app_constants.dart';
import '../models/classe_model.dart';
import '../models/session_model.dart';
import '../utils/app_exceptions.dart';
import 'dio_client.dart';

/// Service enseignant : classes, séances, QR, présences, statistiques.
class TeacherService {
  final DioClient _client;

  TeacherService({DioClient? client}) : _client = client ?? DioClient();

  // ─── Classes ─────────────────────────────────────────────────────────────

  /// Liste les classes de l'enseignant (GET /classes/).
  Future<List<ClasseModel>> fetchClasses() async {
    final response = await _client.get(AppConstants.classesEndpoint);
    final data = _unwrapList(response.data);
    return data.map(ClasseModel.fromJson).toList();
  }

  // ─── Séances ─────────────────────────────────────────────────────────────

  /// Liste les séances (filtrées par la classe pour l'enseignant).
  Future<List<SessionModel>> fetchSessions({int? classeId}) async {
    final params = <String, dynamic>{};
    if (classeId != null) params['classe'] = classeId;
    final response = await _client.get(
      AppConstants.sessionsEndpoint,
      queryParameters: params,
    );
    final data = _unwrapList(response.data);
    return data.map(SessionModel.fromJson).toList();
  }

  Future<SessionModel> fetchSession(int id) async {
    final response = await _client.get(AppConstants.sessionDetailEndpoint(id));
    return SessionModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Crée une séance (POST /sessions/).
  Future<SessionModel> createSession(Map<String, dynamic> payload) async {
    final response = await _client.post(
      AppConstants.sessionsEndpoint,
      data: payload,
    );
    return SessionModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Modifie une séance (PATCH /sessions/{id}/).
  Future<SessionModel> updateSession(
    int id,
    Map<String, dynamic> payload,
  ) async {
    final response = await _client.patch(
      AppConstants.sessionDetailEndpoint(id),
      data: payload,
    );
    return SessionModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Récupère les lieux disponibles pour un créneau donné.
  Future<AvailableLocations> fetchAvailableLocations({
    required String date,
    required String startTime,
    required String endTime,
    String? locationType,
    int? excludeSessionId,
  }) async {
    final params = <String, dynamic>{
      'date': date,
      'start_time': startTime,
      'end_time': endTime,
    };
    if (locationType != null) params['location_type'] = locationType;
    if (excludeSessionId != null) params['exclude_session_id'] = excludeSessionId;
    final response = await _client.get(
      AppConstants.sessionAvailableLocationsEndpoint,
      queryParameters: params,
    );
    final data = response.data;
    if (data is Map<String, dynamic>) return AvailableLocations.fromJson(data);
    return const AvailableLocations();
  }

  // ─── QR ──────────────────────────────────────────────────────────────────

  /// Génère un QR pour une séance (POST /sessions/{id}/generate-qr/).
  Future<SessionQrPayload> generateQr(
    int sessionId, {
    required int expiryMinutes,
    required int attendanceRadiusMeters,
    double? latitude,
    double? longitude,
  }) async {
    final data = <String, dynamic>{
      'expiry_minutes': expiryMinutes,
      'attendance_radius_meters': attendanceRadiusMeters,
    };
    if (latitude != null) data['latitude'] = latitude;
    if (longitude != null) data['longitude'] = longitude;
    final response = await _client.post(
      AppConstants.sessionGenerateQrEndpoint(sessionId),
      data: data,
    );
    return SessionQrPayload.fromJson(response.data as Map<String, dynamic>);
  }

  /// Récupère le QR actif (GET /sessions/{id}/current-qr/).
  Future<SessionQrPayload?> fetchCurrentQr(int sessionId) async {
    try {
      final response = await _client.get(
        AppConstants.sessionCurrentQrEndpoint(sessionId),
      );
      final data = response.data;
      if (data is Map<String, dynamic>) {
        return SessionQrPayload.fromJson(data);
      }
      return null;
    } on NotFoundException {
      return null;
    }
  }

  /// Ferme une séance (POST /sessions/{id}/close/).
  Future<Map<String, dynamic>> closeSession(int sessionId) async {
    final response =
        await _client.post(AppConstants.sessionCloseEndpoint(sessionId));
    return Map<String, dynamic>.from(response.data as Map);
  }

  // ─── Présences ───────────────────────────────────────────────────────────

  /// Présences de l'enseignant (feed "présences en direct").
  Future<List<SessionAttendance>> fetchLiveAttendance() async {
    final response = await _client.get(AppConstants.attendanceEndpoint);
    final data = _unwrapList(response.data);
    return data.map(SessionAttendance.fromJson).toList();
  }

  /// Présences d'une séance.
  Future<List<SessionAttendance>> fetchSessionAttendance(int sessionId) async {
    final response =
        await _client.get(AppConstants.sessionAttendanceEndpoint(sessionId));
    final data = _unwrapList(response.data);
    return data.map(SessionAttendance.fromJson).toList();
  }

  // ─── Statistiques ────────────────────────────────────────────────────────

  /// Statistiques d'une séance.
  Future<SessionStats> fetchSessionStats(int sessionId) async {
    final response =
        await _client.get(AppConstants.sessionStatsEndpoint(sessionId));
    return SessionStats.fromJson(response.data as Map<String, dynamic>);
  }

  /// Tentatives suspectes d'une séance.
  Future<List<SuspiciousAttempt>> fetchSuspiciousAttempts(
    int sessionId,
  ) async {
    final response = await _client.get(
      AppConstants.sessionSuspiciousEndpoint(sessionId),
    );
    final data = _unwrapList(response.data);
    return data.map(SuspiciousAttempt.fromJson).toList();
  }

  /// Statistiques globales (GET /statistics/?period=30).
  Future<GlobalStats> fetchGlobalStats({int period = 30}) async {
    final response = await _client.get(
      AppConstants.statisticsEndpoint,
      queryParameters: {'period': period},
    );
    return GlobalStats.fromJson(response.data as Map<String, dynamic>);
  }

  // ─── Étudiants ───────────────────────────────────────────────────────────

  /// Liste les étudiants d'une classe (GET /students/?classe_id=).
  Future<List<StudentItem>> fetchStudents({int? classeId}) async {
    final params = <String, dynamic>{};
    if (classeId != null) params['classe_id'] = classeId;
    final response = await _client.get(
      '/students/',
      queryParameters: params,
    );
    final data = _unwrapList(response.data);
    return data.map(StudentItem.fromJson).toList();
  }

  // ─── Référentiels (salles / amphis) ─────────────────────────────────────

  Future<List<BlockModel>> fetchBlocks() async {
    final response = await _client.get(AppConstants.blocksEndpoint);
    final data = _unwrapList(response.data);
    return data.map(BlockModel.fromJson).toList();
  }

  Future<List<AmphitheaterModel>> fetchAmphitheaters() async {
    final response = await _client.get(AppConstants.amphitheatersEndpoint);
    final data = _unwrapList(response.data);
    return data.map(AmphitheaterModel.fromJson).toList();
  }

  // ─── Exports ─────────────────────────────────────────────────────────────

  /// Feuille de présence XLSX de la séance (GET /attendance/session/{id}/export/).
  Future<Uint8List> exportSessionXlsx(int sessionId) async {
    return _client.downloadBytes(AppConstants.sessionExportEndpoint(sessionId));
  }

  /// Rapport XLSX de la séance (GET /attendance/session/{id}/report/).
  Future<Uint8List> sessionReportXlsx(int sessionId) async {
    return _client.downloadBytes(AppConstants.sessionReportEndpoint(sessionId));
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  static List<Map<String, dynamic>> _unwrapList(dynamic data) {
    if (data is List) {
      return data.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    if (data is Map<String, dynamic> && data['results'] is List) {
      return (data['results'] as List)
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
    }
    return const [];
  }
}
