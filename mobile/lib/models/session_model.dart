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
      id: (json['id'] as num).toInt(),
      subject: json['subject']?.toString() ?? '',
      moduleId: (json['module_id'] as num?)?.toInt(),
      moduleName: json['module_name']?.toString(),
      teacher: (json['teacher'] as num?)?.toInt(),
      teacherName: json['teacher_name']?.toString() ?? '',
      classe: (json['classe'] as num?)?.toInt(),
      classeName: json['classe_name']?.toString() ?? '',
      classeField: json['classe_field']?.toString() ?? '',
      locationType: json['location_type']?.toString() ?? 'block',
      block: (json['block'] as num?)?.toInt(),
      blockName: json['block_name']?.toString(),
      room: (json['room'] as num?)?.toInt(),
      roomName: json['room_name']?.toString(),
      amphitheater: (json['amphitheater'] as num?)?.toInt(),
      amphitheaterName: json['amphitheater_name']?.toString(),
      date: json['date']?.toString() ?? '',
      startTime: json['start_time']?.toString() ?? '',
      endTime: json['end_time']?.toString() ?? '',
      qrToken: json['qr_token']?.toString(),
      qrSessionId: json['qr_session_id']?.toString() ?? '',
      qrExpiresAt: json['qr_expires_at']?.toString(),
      attendanceRadiusMeters: (json['attendance_radius_meters'] as num?)?.toInt() ?? 50,
      isActive: json['is_active'] as bool? ?? true,
      isClosed: json['is_closed'] as bool? ?? false,
      sessionType: json['session_type']?.toString() ?? 'Cours',
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
      qrToken: json['qr_token']?.toString() ?? '',
      qrSessionId: json['qr_session_id']?.toString() ?? '',
      qrExpiresAt: json['qr_expires_at']?.toString(),
      qrUrl: json['qr_url']?.toString(),
      attendanceRadiusMeters:
          (json['attendance_radius_meters'] as num?)?.toInt() ?? 50,
      locationLatitude: json['location_latitude']?.toString(),
      locationLongitude: json['location_longitude']?.toString(),
      isQrValid: json['is_qr_valid'] as bool? ?? false,
      qrImageBase64: json['qr_image_base64']?.toString(),
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
      sessionId: (json['session_id'] as num?)?.toInt() ?? 0,
      subject: json['subject']?.toString() ?? '',
      totalStudentsInClass: (json['total_students_in_class'] as num?)?.toInt() ?? 0,
      attendanceCount: (json['attendance_count'] as num?)?.toInt() ?? 0,
      attendanceRate: (json['attendance_rate'] as num?)?.toDouble() ?? 0,
      duplicateAttempts: (json['duplicate_attempts'] as num?)?.toInt() ?? 0,
      geofenceViolations: (json['geofence_violations'] as num?)?.toInt() ?? 0,
      suspiciousAttemptsTotal:
          (json['suspicious_attempts_total'] as num?)?.toInt() ?? 0,
      uniqueDevices: (json['unique_devices'] as num?)?.toInt() ?? 0,
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
      id: (json['id'] as num).toInt(),
      session: (json['session'] as num?)?.toInt() ?? 0,
      sessionSubject: json['session_subject']?.toString() ?? '',
      sessionDate: json['session_date']?.toString() ?? '',
      attemptType: json['attempt_type']?.toString() ?? '',
      codeMassar: json['code_massar']?.toString(),
      firstName: json['first_name']?.toString() ?? '',
      lastName: json['last_name']?.toString() ?? '',
      ipAddress: json['ip_address']?.toString(),
      deviceId: json['device_id']?.toString() ?? '',
      errorMessage: json['error_message']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
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
      totalPresent: (json['total_present'] as num?)?.toInt() ?? 0,
      totalAttendance: (json['total_attendance'] as num?)?.toInt() ?? 0,
      attendanceRate: (json['attendance_rate'] as num?)?.toDouble() ?? 0,
      activeClasses: (json['active_classes'] as num?)?.toInt() ?? 0,
      totalStudents: (json['total_students'] as num?)?.toInt() ?? 0,
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
      date: json['date']?.toString() ?? '',
      present: (json['present'] as num?)?.toInt() ?? 0,
      total: (json['total'] as num?)?.toInt() ?? 0,
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
      id: (json['id'] as num).toInt(),
      firstName: json['first_name']?.toString() ?? '',
      lastName: json['last_name']?.toString() ?? '',
      codeMassar: json['code_massar']?.toString() ?? '',
      email: json['email']?.toString(),
      phone: json['phone']?.toString(),
      classeName: json['classe_name']?.toString(),
      classe: (json['classe'] as num?)?.toInt(),
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
      id: (json['id'] as num).toInt(),
      student: (json['student'] as num?)?.toInt() ?? 0,
      session: (json['session'] as num?)?.toInt() ?? 0,
      validationTime: json['validation_time']?.toString() ?? '',
      ipAddress: json['ip_address']?.toString(),
      deviceId: json['device_id']?.toString() ?? '',
      studentDetail: json['student_detail'] != null
          ? StudentDetail.fromJson(
              json['student_detail'] as Map<String, dynamic>)
          : null,
      attendanceStatus: json['attendance_status']?.toString() ?? 'confirmed',
      latitude: (json['latitude'] is num)
          ? (json['latitude'] as num).toDouble()
          : null,
      longitude: (json['longitude'] is num)
          ? (json['longitude'] as num).toDouble()
          : null,
      studentName: json['student_name']?.toString() ?? '',
      studentCodeMassar: json['student_code_massar']?.toString() ?? '',
      subject: json['subject']?.toString() ?? '',
      sessionDate: json['session_date']?.toString() ?? '',
    );
  }
}
