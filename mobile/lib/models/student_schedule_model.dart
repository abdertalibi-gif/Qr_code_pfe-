/// Statut d'une séance dans l'emploi du temps (calculé côté backend).
enum ScheduleStatus {
  upcoming('a_venir', 'À venir'),
  ongoing('en_cours', 'En cours'),
  finished('terminee', 'Terminée'),
  cancelled('annulee', 'Annulée');

  const ScheduleStatus(this.apiValue, this.label);
  final String apiValue;
  final String label;

  static ScheduleStatus fromApi(String? value) {
    switch (value) {
      case 'en_cours':
        return ScheduleStatus.ongoing;
      case 'terminee':
        return ScheduleStatus.finished;
      case 'annulee':
        return ScheduleStatus.cancelled;
      default:
        return ScheduleStatus.upcoming;
    }
  }
}

/// Une séance de l'emploi du temps étudiant
/// (StudentScheduleSerializer — endpoint /attendance/my-schedule/).
class StudentScheduleItem {
  final int id;
  final String subject;
  final String? moduleName;
  final String teacherName;
  final int? classe;
  final String classeName;
  final String locationType;
  final String? blockName;
  final String? roomName;
  final String? amphitheaterName;
  final String date;
  final String startTime;
  final String endTime;
  final String sessionType;
  final bool isActive;
  final bool isClosed;
  final String? qrExpiresAt;
  final bool isWithinSessionWindow;
  final ScheduleStatus status;
  final bool qrOpen;

  const StudentScheduleItem({
    required this.id,
    required this.subject,
    this.moduleName,
    this.teacherName = '',
    this.classe,
    this.classeName = '',
    this.locationType = 'block',
    this.blockName,
    this.roomName,
    this.amphitheaterName,
    this.date = '',
    this.startTime = '',
    this.endTime = '',
    this.sessionType = 'Cours',
    this.isActive = true,
    this.isClosed = false,
    this.qrExpiresAt,
    this.isWithinSessionWindow = false,
    this.status = ScheduleStatus.upcoming,
    this.qrOpen = false,
  });

  factory StudentScheduleItem.fromJson(Map<String, dynamic> json) {
    return StudentScheduleItem(
      id: json['id'] as int,
      subject: json['subject'] as String? ?? '',
      moduleName: json['module_name'] as String?,
      teacherName: json['teacher_name'] as String? ?? '',
      classe: json['classe'] as int?,
      classeName: json['classe_name'] as String? ?? '',
      locationType: json['location_type'] as String? ?? 'block',
      blockName: json['block_name'] as String?,
      roomName: json['room_name'] as String?,
      amphitheaterName: json['amphitheater_name'] as String?,
      date: json['date'] as String? ?? '',
      startTime: json['start_time'] as String? ?? '',
      endTime: json['end_time'] as String? ?? '',
      sessionType: json['session_type'] as String? ?? 'Cours',
      isActive: json['is_active'] as bool? ?? true,
      isClosed: json['is_closed'] as bool? ?? false,
      qrExpiresAt: json['qr_expires_at'] as String?,
      isWithinSessionWindow: json['is_within_session_window'] as bool? ?? false,
      status: ScheduleStatus.fromApi(json['status'] as String?),
      qrOpen: json['qr_open'] as bool? ?? false,
    );
  }

  /// Libellé du type (Cours, TD, TP, Exam, Autre).
  String get sessionTypeLabel {
    switch (sessionType) {
      case 'TD':
        return 'TD';
      case 'TP':
        return 'TP';
      case 'Exam':
        return 'Exam';
      case 'Other':
        return 'Autre';
      default:
        return 'Cours';
    }
  }

  /// Nom du module (module_name sinon subject).
  String get title => (moduleName != null && moduleName!.isNotEmpty)
      ? moduleName!
      : (subject.isNotEmpty ? subject : 'Séance #$id');

  /// Lieu affichable (Amphi X / Bloc — Salle).
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

  String get timeRange => '$startTime – $endTime';

  /// Créneaux horaires en minutes pour un affichage vertical.
  int get startMinutes {
    final parts = startTime.split(':');
    if (parts.length < 2) return 0;
    final h = int.tryParse(parts[0]) ?? 0;
    final m = int.tryParse(parts[1]) ?? 0;
    return h * 60 + m;
  }

  int get endMinutes {
    final parts = endTime.split(':');
    if (parts.length < 2) return 0;
    final h = int.tryParse(parts[0]) ?? 0;
    final m = int.tryParse(parts[1]) ?? 0;
    return h * 60 + m;
  }
}
