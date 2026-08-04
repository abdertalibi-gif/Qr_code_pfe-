import '../constants/app_constants.dart';
import '../models/classe_model.dart';
import '../models/attendance_model.dart';
import 'dio_client.dart';

/// Service étudiant : QR, profil, historique, emploi du temps, statistiques.
class StudentService {
  final DioClient _client;

  StudentService({DioClient? client}) : _client = client ?? DioClient();

  // ─── Enregistrement ─────────────────────────────────────────────────────────

  /// Scanne un QR depuis l'application mobile (validé par l'app).
  Future<Map<String, dynamic>> validateFromApp({
    required String qrToken,
    double? latitude,
    double? longitude,
  }) async {
    final response = await _client.post(
      AppConstants.validateAppAttendanceEndpoint,
      data: {
        'qr_token': qrToken,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  /// Scanne un QR public (fallback).
  Future<Map<String, dynamic>> validatePublic({
    required String qrToken,
    required String firstName,
    required String lastName,
    required String codeMassar,
    double? latitude,
    double? longitude,
  }) async {
    final response = await _client.post(
      AppConstants.validateAttendanceEndpoint,
      data: {
        'qr_token': qrToken,
        'first_name': firstName.trim(),
        'last_name': lastName.trim(),
        'code_massar': codeMassar.trim(),
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  // ─── Profil et informations personnelles ────────────────────────────────────

  /// Récupère les informations du student (depuis /me/).
  Future<Map<String, dynamic>> fetchStudentProfile() async {
    final response = await _client.get(AppConstants.meEndpoint);
    return response.data as Map<String, dynamic>;
  }

  /// Liste les modules / filières du student (curriculum).
  Future<List<Map<String, dynamic>>> fetchModules() async {
    final response = await _client.get(AppConstants.curriculumEndpoint);
    final data = _unwrapList(response.data);
    return data.cast<Map<String, dynamic>>();
  }

  /// Charge l'emploi du temps / classes du student.
  Future<List<ClasseModel>> fetchSchedule() async {
    // Utiliser /classes/?assigne au teacher du student.
    final response = await _client.get(AppConstants.classesEndpoint);
    final data = _unwrapList(response.data);
    return data.map(ClasseModel.fromJson).toList();
  }

  // ─── Présences ─────────────────────────────────────────────────────────────

  /// Historique des présences du student.
  Future<List<AttendanceModel>> fetchMyAttendance() async {
    final response = await _client.get(AppConstants.myAttendanceEndpoint);
    final data = _unwrapList(response.data);
    return data.map(AttendanceModel.fromJson).toList();
  }

  // ─── Statistiques personnelles ─────────────────────────────────────────────

  /// Statistiques personnelles du student (pourrait appeler /statistics/ avec le student id).
  Future<Map<String, dynamic>> fetchPersonalStats() async {
    final response = await _client.get(AppConstants.statisticsEndpoint);
    return response.data as Map<String, dynamic>;
  }

  // ─── QR personnel ────────────────────────────────────────────────────────────

  /// Génère un QR personnel.
  /// Endpoint backend : POST /students/{id}/generate-personal-qr/ (si dispo).
  Future<Map<String, dynamic>> generatePersonalQr() async {
    final response = await _client.post('/students/generate-personal-qr/');
    return response.data as Map<String, dynamic>;
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