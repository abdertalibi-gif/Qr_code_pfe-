class StudentProfile {
  final int id;
  final String firstName;
  final String lastName;
  final String codeMassar;
  final int? classeId;
  final String? classeName;

  StudentProfile({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.codeMassar,
    this.classeId,
    this.classeName,
  });

  factory StudentProfile.fromJson(Map<String, dynamic> json) {
    return StudentProfile(
      id: json['id'] as int,
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      codeMassar: json['code_massar'] as String? ?? '',
      classeId: json['classe_id'] as int?,
      classeName: json['classe_name'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'first_name': firstName,
        'last_name': lastName,
        'code_massar': codeMassar,
        'classe_id': classeId,
        'classe_name': classeName,
      };
}

class UserModel {
  final int id;
  final String firstName;
  final String lastName;
  final String email;
  final String role;
  final String createdAt;
  final StudentProfile? studentProfile;
  final String phone;
  final String? cin;
  final String grade;
  final String speciality;
  final int? departmentId;
  final String? departmentName;
  final List<int> assignedClassIds;

  UserModel({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.role,
    required this.createdAt,
    this.studentProfile,
    this.phone = '',
    this.cin,
    this.grade = '',
    this.speciality = '',
    this.departmentId,
    this.departmentName,
    this.assignedClassIds = const [],
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    StudentProfile? profile;
    final rawProfile = json['student_profile'];
    if (rawProfile is Map<String, dynamic>) {
      profile = StudentProfile.fromJson(rawProfile);
    }
    return UserModel(
      id: json['id'] as int,
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      role: json['role'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
      studentProfile: profile,
      phone: json['phone'] as String? ?? '',
      cin: json['cin'] as String?,
      grade: json['grade'] as String? ?? '',
      speciality: json['speciality'] as String? ?? '',
      departmentId: json['department_id'] as int?,
      departmentName: json['department_name'] as String?,
      assignedClassIds: _readIntList(json['assigned_class_ids']),
    );
  }

  static List<int> _readIntList(dynamic value) {
    if (value is List) {
      return value
          .whereType<num>()
          .map((e) => e.toInt())
          .toList();
    }
    return const [];
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'first_name': firstName,
        'last_name': lastName,
        'email': email,
        'role': role,
        'created_at': createdAt,
        'phone': phone,
        'cin': cin,
        'grade': grade,
        'speciality': speciality,
        'department_id': departmentId,
        'department_name': departmentName,
        'assigned_class_ids': assignedClassIds,
        if (studentProfile != null) 'student_profile': studentProfile!.toJson(),
      };

  String get fullName => '$firstName $lastName'.trim();

  String get initials {
    final f = firstName.isNotEmpty ? firstName[0].toUpperCase() : '';
    final l = lastName.isNotEmpty ? lastName[0].toUpperCase() : '';
    return '$f$l';
  }

  bool get isAdmin => role == 'admin';
  bool get isTeacher => role == 'teacher';
  bool get isStudent => role == 'student';

  UserModel copyWith({
    int? id,
    String? firstName,
    String? lastName,
    String? email,
    String? role,
    String? createdAt,
    String? phone,
    String? cin,
    String? grade,
    String? speciality,
    int? departmentId,
    String? departmentName,
    List<int>? assignedClassIds,
  }) {
    return UserModel(
      id: id ?? this.id,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      email: email ?? this.email,
      role: role ?? this.role,
      createdAt: createdAt ?? this.createdAt,
      studentProfile: studentProfile,
      phone: phone ?? this.phone,
      cin: cin ?? this.cin,
      grade: grade ?? this.grade,
      speciality: speciality ?? this.speciality,
      departmentId: departmentId ?? this.departmentId,
      departmentName: departmentName ?? this.departmentName,
      assignedClassIds: assignedClassIds ?? this.assignedClassIds,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is UserModel && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'UserModel(id: $id, email: $email, role: $role, name: $fullName)';
}
