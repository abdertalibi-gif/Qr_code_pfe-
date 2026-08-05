import '../constants/app_constants.dart';
import '../models/attendance_model.dart';
import '../models/student_schedule_model.dart';
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

  /// Emploi du temps dynamique de l'étudiant (GET /attendance/my-schedule/).
  ///
  /// Renvoie les séances de la classe de l'étudiant avec leur statut calculé
  /// (a_venir / en_cours / terminee / annulee) et l'indicateur `qrOpen`.
  Future<List<StudentScheduleItem>> fetchMySchedule() async {
    final response = await _client.get(AppConstants.myScheduleEndpoint);
    final data = _unwrapList(response.data);
    return data.map(StudentScheduleItem.fromJson).toList();
  }

  // ─── Présences ─────────────────────────────────────────────────────────────

  /// Historique des présences du student.
  Future<List<AttendanceModel>> fetchMyAttendance() async {
    final response = await _client.get(AppConstants.myAttendanceEndpoint);
    final data = _unwrapList(response.data);
    return data.map(AttendanceModel.fromJson).toList();
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