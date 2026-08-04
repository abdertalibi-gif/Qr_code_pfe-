import 'attendance_model.dart';

/// Type de séance.
enum SessionType {
  cours('Cours'),
  td('TD'),
  tp('TP'),
  exam('Exam'),
  other('Other');

  const SessionType(this.label);
  final String label;

  static SessionType fromApi(String? value) {
    switch (value) {
      case 'TD':
        return SessionType.td;
      case 'TP':
        return SessionType.tp;
      case 'Exam':
        return SessionType.exam;
      case 'Other':
        return SessionType.other;
      default:
        return SessionType.cours;
    }
  }

  String get apiValue => switch (this) {
        SessionType.cours => 'Cours',
        SessionType.td => 'TD',
        SessionType.tp => 'TP',
        SessionType.exam => 'Exam',
        SessionType.other => 'Other',
      };
}

/// Type de lieu d'une séance.
enum LocationType {
  block('block'),
  amphitheater('amphitheater');

  const LocationType(this.apiValue);
  final String apiValue;

  static LocationType fromApi(String? value) =>
      value == 'amphitheater' ? LocationType.amphitheater : LocationType.block;
}

/// Une séance (SessionSerializer) — vue enseignant.
class SessionModel {
  final int id;
  final String subject;
  final int? moduleId;
  final String? moduleName;
  final int? teacher;
  final String teacherName;
  final int? classe;
  final String classeName;
  final String classeField;
  final String locationType;
  final int? block;
  final String? blockName;
  final int? room;
  final String? roomName;
  final int? amphitheater;
  final String? amphitheaterName;
  final String date;
  final String startTime;
  final String endTime;
  final String? qrToken;
  final String qrSessionId;
  final String? qrExpiresAt;
  final int attendanceRadiusMeters;
  final bool isActive;
  final bool isClosed;
  final String sessionType;
  final bool isQrValid;
  final bool isWithinSessionWindow;
  final bool canGenerateQr;

  const SessionModel({
    required this.id,
    required this.subject,
    this.moduleId,
    this.moduleName,
    this.teacher,
    this.teacherName = '',
    this.classe,
    this.classeName = '',
    this.classeField = '',
    this.locationType = 'block',
    this.block,
    this.blockName,
    this.room,
    this.roomName,
    this.amphitheater,
    this.amphitheaterName,
    this.date = '',
    this.startTime = '',
    this.endTime = '',
    this.qrToken,
    this.qrSessionId = '',
    this.qrExpiresAt,
    this.attendanceRadiusMeters = 50,
    this.isActive = true,
    this.isClosed = false,
    this.sessionType = 'Cours',
    this.isQrValid = false,
    this.isWithinSessionWindow = false,
    this.canGenerateQr = false,
  });

  factory SessionModel.fromJson(Map<String, dynamic> json) {
    return SessionModel(
      id: json['id'] as int,
      subject: json['subject'] as String? ?? '',
      moduleId: json['module_id'] as int?,
      moduleName: json['module_name'] as String?,
      teacher: json['teacher'] as int?,
      teacherName: json['teacher_name'] as String? ?? '',
      classe: json['classe'] as int?,
      classeName: json['classe_name'] as String? ?? '',
      classeField: json['classe_field'] as String? ?? '',
      locationType: json['location_type'] as String? ?? 'block',
      block: json['block'] as int?,
      blockName: json['block_name'] as String?,
      room: json['room'] as int?,
      roomName: json['room_name'] as String?,
      amphitheater: json['amphitheater'] as int?,
      amphitheaterName: json['amphitheater_name'] as String?,
      date: json['date'] as String? ?? '',
      startTime: json['start_time'] as String? ?? '',
      endTime: json['end_time'] as String? ?? '',
      qrToken: json['qr_token'] as String?,
      qrSessionId: json['qr_session_id'] as String? ?? '',
      qrExpiresAt: json['qr_expires_at'] as String?,
      attendanceRadiusMeters: json['attendance_radius_meters'] as int? ?? 50,
      isActive: json['is_active'] as bool? ?? true,
      isClosed: json['is_closed'] as bool? ?? false,
      sessionType: json['session_type'] as String? ?? 'Cours',
      isQrValid: json['is_qr_valid'] as bool? ?? false,
      isWithinSessionWindow: json['is_within_session_window'] as bool? ?? false,
      canGenerateQr: json['can_generate_qr'] as bool? ?? false,
    );
  }

  String get timeRange => '$startTime – $endTime';

  String get locationDisplay {
    if (amphitheaterName != null && amphitheaterName!.isNotEmpty) {
      return 'Amphi $amphitheaterName';
    }
    final parts = <String>[
      if (blockName != null && blockName!.isNotEmpty) blockName!,
      if (roomName != null && roomName!.isNotEmpty) roomName!,
    ];
    return parts.isNotEmpty ? parts.join(' — ') : '—';
  }

  SessionType get sessionTypeEnum => SessionType.fromApi(sessionType);

  DateTime? get dateTime {
    return DateTime.tryParse('$date $startTime');
  }

  DateTime? get dateTimeEnd {
    return DateTime.tryParse('$date $endTime');
  }
}

/// Résultat de la génération d'un QR (POST generate-qr / GET current-qr).
class SessionQrPayload {
  final String qrToken;
  final String qrSessionId;
  final String? qrExpiresAt;
  final String? qrUrl;
  final int attendanceRadiusMeters;
  final String? locationLatitude;
  final String? locationLongitude;
  final bool isQrValid;
  final String? qrImageBase64;

  const SessionQrPayload({
    required this.qrToken,
    required this.qrSessionId,
    this.qrExpiresAt,
    this.qrUrl,
    this.attendanceRadiusMeters = 50,
    this.locationLatitude,
    this.locationLongitude,
    this.isQrValid = false,
    this.qrImageBase64,
  });

  factory SessionQrPayload.fromJson(Map<String, dynamic> json) {
    return SessionQrPayload(
      qrToken: json['qr_token'] as String? ?? '',
      qrSessionId: json['qr_session_id'] as String? ?? '',
      qrExpiresAt: json['qr_expires_at'] as String?,
      qrUrl: json['qr_url'] as String?,
      attendanceRadiusMeters:
          json['attendance_radius_meters'] as int? ?? 50,
      locationLatitude: json['location_latitude'] as String?,
      locationLongitude: json['location_longitude'] as String?,
      isQrValid: json['is_qr_valid'] as bool? ?? false,
      qrImageBase64: json['qr_image_base64'] as String?,
    );
  }

  /// Renvoie le payload de la réponse générée par le backend.
  DateTime? get expiresAt {
    try {
      return DateTime.parse(qrExpiresAt ?? '').toLocal();
    } catch (_) {
      return null;
    }
  }
}

/// Statistiques d'une séance (GET /attendance/session/{id}/stats/).
class SessionStats {
  final int sessionId;
  final String subject;
  final int totalStudentsInClass;
  final int attendanceCount;
  final double attendanceRate;
  final int duplicateAttempts;
  final int geofenceViolations;
  final int suspiciousAttemptsTotal;
  final int uniqueDevices;
  final List<LocationPoint> locations;

  const SessionStats({
    required this.sessionId,
    this.subject = '',
    this.totalStudentsInClass = 0,
    this.attendanceCount = 0,
    this.attendanceRate = 0,
    this.duplicateAttempts = 0,
    this.geofenceViolations = 0,
    this.suspiciousAttemptsTotal = 0,
    this.uniqueDevices = 0,
    this.locations = const [],
  });

  factory SessionStats.fromJson(Map<String, dynamic> json) {
    final rawLocations = json['locations'];
    return SessionStats(
      sessionId: json['session_id'] as int? ?? 0,
      subject: json['subject'] as String? ?? '',
      totalStudentsInClass: json['total_students_in_class'] as int? ?? 0,
      attendanceCount: json['attendance_count'] as int? ?? 0,
      attendanceRate: (json['attendance_rate'] as num?)?.toDouble() ?? 0,
      duplicateAttempts: json['duplicate_attempts'] as int? ?? 0,
      geofenceViolations: json['geofence_violations'] as int? ?? 0,
      suspiciousAttemptsTotal:
          json['suspicious_attempts_total'] as int? ?? 0,
      uniqueDevices: json['unique_devices'] as int? ?? 0,
      locations: rawLocations is List
          ? rawLocations
              .map((e) => LocationPoint.fromJson(e as Map<String, dynamic>))
              .toList()
          : const [],
    );
  }
}

/// Point de localisation d'un étudiant scanné.
class LocationPoint {
  final String studentName;
  final String codeMassar;
  final String? latitude;
  final String? longitude;
  final String validationTime;

  const LocationPoint({
    required this.studentName,
    required this.codeMassar,
    this.latitude,
    this.longitude,
    this.validationTime = '',
  });

  factory LocationPoint.fromJson(Map<String, dynamic> json) {
    return LocationPoint(
      studentName: json['student_name'] as String? ?? '',
      codeMassar: json['code_massar'] as String? ?? '',
      latitude: json['latitude']?.toString(),
      longitude: json['longitude']?.toString(),
      validationTime: json['validation_time'] as String? ?? '',
    );
  }

  double? get lat => double.tryParse(latitude ?? '');
  double? get lng => double.tryParse(longitude ?? '');
}

/// Tentative suspecte (GET /attendance/session/{id}/suspicious/).
class SuspiciousAttempt {
  final int id;
  final int session;
  final String sessionSubject;
  final String sessionDate;
  final String attemptType;
  final String? codeMassar;
  final String firstName;
  final String lastName;
  final String? ipAddress;
  final String deviceId;
  final String? errorMessage;
  final String createdAt;

  const SuspiciousAttempt({
    required this.id,
    required this.session,
    this.sessionSubject = '',
    this.sessionDate = '',
    this.attemptType = '',
    this.codeMassar,
    this.firstName = '',
    this.lastName = '',
    this.ipAddress,
    this.deviceId = '',
    this.errorMessage,
    this.createdAt = '',
  });

  factory SuspiciousAttempt.fromJson(Map<String, dynamic> json) {
    return SuspiciousAttempt(
      id: json['id'] as int,
      session: json['session'] as int? ?? 0,
      sessionSubject: json['session_subject'] as String? ?? '',
      sessionDate: json['session_date'] as String? ?? '',
      attemptType: json['attempt_type'] as String? ?? '',
      codeMassar: json['code_massar'] as String?,
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      ipAddress: json['ip_address'] as String?,
      deviceId: json['device_id'] as String? ?? '',
      errorMessage: json['error_message'] as String?,
      createdAt: json['created_at'] as String? ?? '',
    );
  }

  String get studentName => '$firstName $lastName'.trim();

  String get typeLabel {
    switch (attemptType) {
      case 'duplicate_student':
        return 'Doublon étudiant';
      case 'duplicate_device':
        return 'Doublon appareil';
      case 'geofence_violation':
        return 'Hors zone';
      case 'expired_qr':
        return 'QR expiré';
      case 'invalid_token':
        return 'QR invalide';
      case 'inactive_session':
        return 'Séance inactive';
      case 'identity_mismatch':
        return 'Identité non reconnue';
      case 'class_mismatch':
        return 'Classe différente';
      case 'unknown_student':
        return 'Étudiant inconnu';
      default:
        return attemptType.replaceAll('_', ' ');
    }
  }
}

/// Statistiques globales (GET /statistics/?period=30).
class GlobalStats {
  final int totalPresent;
  final int totalAttendance;
  final double attendanceRate;
  final int activeClasses;
  final int totalStudents;
  final List<DailyAttendance> daily;

  const GlobalStats({
    this.totalPresent = 0,
    this.totalAttendance = 0,
    this.attendanceRate = 0,
    this.activeClasses = 0,
    this.totalStudents = 0,
    this.daily = const [],
  });

  factory GlobalStats.fromJson(Map<String, dynamic> json) {
    final rawDaily = json['daily_attendance'];
    return GlobalStats(
      totalPresent: json['total_present'] as int? ?? 0,
      totalAttendance: json['total_attendance'] as int? ?? 0,
      attendanceRate: (json['attendance_rate'] as num?)?.toDouble() ?? 0,
      activeClasses: json['active_classes'] as int? ?? 0,
      totalStudents: json['total_students'] as int? ?? 0,
      daily: rawDaily is List
          ? rawDaily
              .map((e) => DailyAttendance.fromJson(e as Map<String, dynamic>))
              .toList()
          : const [],
    );
  }

  int get totalAbsent =>
      totalAttendance > totalPresent ? totalAttendance - totalPresent : 0;
}

class DailyAttendance {
  final String date;
  final int present;
  final int total;

  const DailyAttendance({
    required this.date,
    this.present = 0,
    this.total = 0,
  });

  factory DailyAttendance.fromJson(Map<String, dynamic> json) {
    return DailyAttendance(
      date: json['date'] as String? ?? '',
      present: json['present'] as int? ?? 0,
      total: json['total'] as int? ?? 0,
    );
  }
}

/// Liste d'étudiants d'une séance / classe (StudentSerializer / ModuleStudentSerializer).
class StudentItem {
  final int id;
  final String firstName;
  final String lastName;
  final String codeMassar;
  final String? email;
  final String? phone;
  final String? classeName;
  final int? classe;

  const StudentItem({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.codeMassar,
    this.email,
    this.phone,
    this.classeName,
    this.classe,
  });

  factory StudentItem.fromJson(Map<String, dynamic> json) {
    return StudentItem(
      id: json['id'] as int,
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      codeMassar: json['code_massar'] as String? ?? '',
      email: json['email'] as String?,
      phone: json['phone'] as String?,
      classeName: json['classe_name'] as String?,
      classe: json['classe'] as int?,
    );
  }

  String get fullName => '$firstName $lastName'.trim();
}

/// Une présence (réutilise AttendanceModel mais avec les champs étendus).
class SessionAttendance extends AttendanceModel {
  final String studentName;
  final String studentCodeMassar;
  final String subject;
  final String sessionDate;

SessionAttendance({
    required super.id,
    required super.student,
    required super.session,
    required super.validationTime,
    super.ipAddress,
    super.deviceId = '',
    super.studentDetail,
    super.attendanceStatus = 'confirmed',
    super.latitude,
    super.longitude,
    this.studentName = '',
    this.studentCodeMassar = '',
    this.subject = '',
    this.sessionDate = '',
  });

  factory SessionAttendance.fromJson(Map<String, dynamic> json) {
    return SessionAttendance(
      id: json['id'] as int,
      student: json['student'] as int? ?? 0,
      session: json['session'] as int? ?? 0,
      validationTime: json['validation_time'] as String? ?? '',
      ipAddress: json['ip_address'] as String?,
      deviceId: json['device_id'] as String? ?? '',
      studentDetail: json['student_detail'] != null
          ? StudentDetail.fromJson(
              json['student_detail'] as Map<String, dynamic>)
          : null,
      attendanceStatus: json['attendance_status'] as String? ?? 'confirmed',
      latitude: (json['latitude'] is num)
          ? (json['latitude'] as num).toDouble()
          : null,
      longitude: (json['longitude'] is num)
          ? (json['longitude'] as num).toDouble()
          : null,
      studentName: json['student_name'] as String? ?? '',
      studentCodeMassar: json['student_code_massar'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      sessionDate: json['session_date'] as String? ?? '',
    );
  }
}
