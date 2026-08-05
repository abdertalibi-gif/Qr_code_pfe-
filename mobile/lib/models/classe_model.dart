/// Un module / matière (ModuleSerializer).
class ModuleItem {
  final int id;
  final String name;
  final String? code;
  final int? filiereId;
  final String? filiereName;

  const ModuleItem({
    required this.id,
    required this.name,
    this.code,
    this.filiereId,
    this.filiereName,
  });

  factory ModuleItem.fromJson(Map<String, dynamic> json) {
    return ModuleItem(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      code: json['code'] as String?,
      filiereId: json['filiere_id'] as int?,
      filiereName: json['filiere_name'] as String?,
    );
  }
}

/// Une classe (ClasseSerializer) — réutilisée par l'enseignant.
class ClasseModel {
  final int id;
  final String name;
  final String code;
  final String niveau;
  final int? filiereId;
  final String? filiereName;
  final int? semestreId;
  final String? semestreName;
  final int? moduleId;
  final String? moduleName;
  final int? teacherId;
  final String? teacherName;
  final int? departmentId;
  final String? departmentName;
  final int studentCount;
  final int teacherCount;
  final String academicYear;
  final String level;
  final String field;
  final String locationType;
  final int? blockId;
  final int? roomId;
  final int? amphitheaterId;

  const ClasseModel({
    required this.id,
    required this.name,
    this.code = '',
    this.niveau = '',
    this.filiereId,
    this.filiereName,
    this.semestreId,
    this.semestreName,
    this.moduleId,
    this.moduleName,
    this.teacherId,
    this.teacherName,
    this.departmentId,
    this.departmentName,
    this.studentCount = 0,
    this.teacherCount = 0,
    this.academicYear = '',
    this.level = '',
    this.field = '',
    this.locationType = '',
    this.blockId,
    this.roomId,
    this.amphitheaterId,
  });

  factory ClasseModel.fromJson(Map<String, dynamic> json) {
    return ClasseModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      code: json['code'] as String? ?? '',
      niveau: json['niveau_id'] as String? ?? '',
      filiereId: json['filiere_id'] as int?,
      filiereName: json['filiere_name'] as String?,
      semestreId: json['semestre_id'] as int?,
      semestreName: json['semestre_name'] as String?,
      moduleId: json['module_id'] as int?,
      moduleName: json['module_name'] as String?,
      teacherId: json['teacher_id'] as int?,
      teacherName: json['teacher_name'] as String?,
      departmentId: json['department_id'] as int?,
      departmentName: json['department_name'] as String?,
      studentCount: json['student_count'] as int? ?? 0,
      teacherCount: json['teacher_count'] as int? ?? 0,
      academicYear: json['academic_year'] as String? ?? '',
      level: json['level'] as String? ?? '',
      field: json['field'] as String? ?? '',
      locationType: json['location_type'] as String? ?? '',
      blockId: json['block_id'] as int?,
      roomId: json['room_id'] as int?,
      amphitheaterId: json['amphitheater_id'] as int?,
    );
  }

  String get subtitle {
    final parts = <String>[
      if (filiereName != null && filiereName!.isNotEmpty) filiereName!,
      if (semestreName != null && semestreName!.isNotEmpty) semestreName!,
      if (academicYear.isNotEmpty) academicYear,
    ];
    return parts.join(' · ');
  }
}

/// Bloc avec ses salles (GET /blocks/).
class BlockRoom {
  final int id;
  final String name;
  final int? blockId;

  const BlockRoom({required this.id, required this.name, this.blockId});

  factory BlockRoom.fromJson(Map<String, dynamic> json) => BlockRoom(
        id: json['id'] as int,
        name: json['name'] as String? ?? '',
        blockId: json['block'] as int?,
      );
}

/// Bloc contenant des salles.
class BlockModel {
  final int id;
  final String name;
  final List<BlockRoom> rooms;

  const BlockModel({required this.id, required this.name, this.rooms = const []});

  factory BlockModel.fromJson(Map<String, dynamic> json) {
    final rawRooms = json['rooms'];
    return BlockModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      rooms: rawRooms is List
          ? rawRooms
              .map((e) => BlockRoom.fromJson(e as Map<String, dynamic>))
              .toList()
          : const [],
    );
  }
}

/// Amphithéâtre (GET /amphitheaters/).
class AmphitheaterModel {
  final int id;
  final String name;

  const AmphitheaterModel({required this.id, required this.name});

  factory AmphitheaterModel.fromJson(Map<String, dynamic> json) =>
      AmphitheaterModel(
        id: json['id'] as int,
        name: json['name'] as String? ?? '',
      );
}

/// Disponibilités des lieux (GET /sessions/available-locations/).
class AvailableLocations {
  final List<BlockRoom> rooms;
  final List<BlockModel> blocks;
  final List<AmphitheaterModel> amphitheaters;

  const AvailableLocations({
    this.rooms = const [],
    this.blocks = const [],
    this.amphitheaters = const [],
  });

  factory AvailableLocations.fromJson(Map<String, dynamic> json) {
    return AvailableLocations(
      rooms: _list(json['rooms']).map(BlockRoom.fromJson).toList(),
      blocks: _list(json['blocks']).map(BlockModel.fromJson).toList(),
      amphitheaters:
          _list(json['amphitheaters']).map(AmphitheaterModel.fromJson).toList(),
    );
  }

  static List<Map<String, dynamic>> _list(dynamic value) {
    if (value is List) {
      return value.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    return const [];
  }
}
