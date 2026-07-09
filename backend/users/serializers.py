from django.contrib.auth import authenticate
from django.contrib.auth.backends import ModelBackend
from django.utils import timezone
from rest_framework import serializers

from curriculum.models import Filiere, Module, Semestre
from users.models import NIVEAU_SEMESTRE_MAP
from .models import Amphitheater, Block, Classe, Department, Room, Student, StudentModuleEnrollment, User


class EmailBackend(ModelBackend):
    """Custom authentication backend that uses email instead of username"""
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()
    filiere_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "head", "head_name", "filiere_count"]

    def get_head_name(self, obj):
        if obj.head:
            return f"{obj.head.first_name} {obj.head.last_name}"
        return None

    def get_filiere_count(self, obj):
        return obj.filieres.count()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        email = data.get("email", "").lower().strip()
        password = data.get("password", "")

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )
        
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        data["user"] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    student_profile = serializers.SerializerMethodField()
    assigned_class_ids = serializers.PrimaryKeyRelatedField(
        source="assigned_classes",
        many=True,
        queryset=Classe.objects.all(),
        required=False,
    )
    managed_department = serializers.SerializerMethodField()
    managed_filieres = serializers.SerializerMethodField()
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "cin",
            "grade",
            "speciality",
            "role",
            "is_active",
            "is_also_teacher",
            "assigned_class_ids",
            "student_profile",
            "managed_department",
            "managed_filieres",
            "department_id",
            "department_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_full_name(self, obj):
        return obj.full_name

    def get_student_profile(self, obj):
        if obj.role != "student":
            return None
        try:
            profile = obj.student_profile
        except Student.DoesNotExist:
            return None
        if profile is None:
            return None
        return {
            "id": profile.id,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "code_massar": profile.code_massar,
            "code_apogee": profile.code_apogee,
            "classe_id": profile.classe_id,
            "classe_name": str(profile.classe) if profile.classe else "",
        }

    def get_managed_department(self, obj):
        dept = obj.headed_department.first()
        if dept is None:
            return None
        return {"id": dept.id, "name": dept.name}

    def get_managed_filieres(self, obj):
        return [
            {"id": f.id, "name": f.name}
            for f in obj.managed_filieres.all()
        ]

    def validate_assigned_class_ids(self, value):
        if self.instance and self.instance.role not in ("teacher", "department_head", "program_manager") and value:
            raise serializers.ValidationError(
                "Seuls les enseignants, chefs de département et responsables de filière peuvent être affectés à des classes."
            )
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
    )
    assigned_class_ids = serializers.PrimaryKeyRelatedField(
        source="assigned_classes",
        many=True,
        queryset=Classe.objects.all(),
        required=False,
    )
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )
    filiere_id = serializers.PrimaryKeyRelatedField(
        source="filiere",
        queryset=Filiere.objects.all(),
        required=False,
        allow_null=True,
    )
    is_department_head = serializers.BooleanField(required=False, default=False)
    is_program_manager = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "role",
            "password",
            "password_confirm",
            "assigned_class_ids",
            "department_id",
            "filiere_id",
            "is_also_teacher",
            "is_department_head",
            "is_program_manager",
        ]

    def validate(self, data):
        password = data.get("password")
        password_confirm = data.get("password_confirm")
        if password_confirm is not None and password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        data.pop("password_confirm", None)
        assigned = data.get("assigned_classes", [])
        role = data.get("role", "teacher")
        can_have_classes = ("teacher", "department_head", "program_manager")
        if role not in can_have_classes and assigned:
            raise serializers.ValidationError(
                {"assigned_class_ids": "Seuls les enseignants, chefs de département et responsables de filière peuvent avoir des classes."}
            )
        department = data.get("department")
        filiere = data.get("filiere")
        is_dept_head = data.get("is_department_head", False)
        is_prog_mgr = data.get("is_program_manager", False)
        if role == "department_head" and not department:
            raise serializers.ValidationError(
                {"department_id": "Le département est obligatoire pour le chef de département."}
            )
        if role == "program_manager" and not filiere:
            raise serializers.ValidationError(
                {"filiere_id": "La filière est obligatoire pour le responsable de filière."}
            )
        if role == "teacher" and is_dept_head and not department:
            raise serializers.ValidationError(
                {"department_id": "Le département est obligatoire pour un enseignant chef de département."}
            )
        if role == "teacher" and is_prog_mgr and not filiere:
            raise serializers.ValidationError(
                {"filiere_id": "La filière est obligatoire pour un enseignant responsable de filière."}
            )
        if role != "teacher":
            data.pop("is_also_teacher", None)
        return data

    def create(self, validated_data):
        role = validated_data.get("role", "teacher")
        assigned_classes = validated_data.pop("assigned_classes", [])
        department = validated_data.pop("department", None)
        filiere = validated_data.pop("filiere", None)
        is_dept_head = validated_data.pop("is_department_head", False)
        is_prog_mgr = validated_data.pop("is_program_manager", False)
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if assigned_classes:
            user.assigned_classes.set(assigned_classes)
        if department and (role == "department_head" or (role == "teacher" and is_dept_head)):
            if department.head and department.head != user:
                raise serializers.ValidationError(
                    {"department_id": "Ce département a déjà un chef."}
                )
            department.head = user
            department.save(update_fields=["head"])
        if filiere and (role == "program_manager" or (role == "teacher" and is_prog_mgr)):
            if filiere.manager and filiere.manager != user:
                raise serializers.ValidationError(
                    {"filiere_id": "Cette filière a déjà un responsable."}
                )
            filiere.manager = user
            filiere.save(update_fields=["manager"])
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
    )
    assigned_class_ids = serializers.PrimaryKeyRelatedField(
        source="assigned_classes",
        many=True,
        queryset=Classe.objects.all(),
        required=False,
    )
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )
    filiere_id = serializers.PrimaryKeyRelatedField(
        source="filiere",
        queryset=Filiere.objects.all(),
        required=False,
        allow_null=True,
    )
    is_department_head = serializers.BooleanField(required=False, default=False)
    is_program_manager = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "password",
            "assigned_class_ids",
            "department_id",
            "filiere_id",
            "is_also_teacher",
            "is_department_head",
            "is_program_manager",
        ]

    def validate(self, data):
        role = data.get("role", getattr(self.instance, "role", None))
        assigned = data.get("assigned_classes")
        can_have_classes = ("teacher", "department_head", "program_manager")
        if assigned is not None and role not in can_have_classes and assigned:
            raise serializers.ValidationError(
                {"assigned_class_ids": "Seuls les enseignants, chefs de département et responsables de filière peuvent avoir des classes."}
            )
        department = data.get("department")
        filiere = data.get("filiere")
        is_dept_head = data.get("is_department_head", False)
        is_prog_mgr = data.get("is_program_manager", False)
        if role == "teacher" and is_dept_head and not department:
            raise serializers.ValidationError(
                {"department_id": "Le département est obligatoire pour un enseignant chef de département."}
            )
        if role == "teacher" and is_prog_mgr and not filiere:
            raise serializers.ValidationError(
                {"filiere_id": "La filière est obligatoire pour un enseignant responsable de filière."}
            )
        if role != "teacher":
            data.pop("is_also_teacher", None)
        return data

    def update(self, instance, validated_data):
        assigned_classes = validated_data.pop("assigned_classes", None)
        department = validated_data.pop("department", None)
        filiere = validated_data.pop("filiere", None)
        is_dept_head = validated_data.pop("is_department_head", False)
        is_prog_mgr = validated_data.pop("is_program_manager", False)
        password = validated_data.pop("password", None)
        role = validated_data.get("role", instance.role)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if assigned_classes is not None:
            instance.assigned_classes.set(assigned_classes)
        if department is not None and (role == "department_head" or (role == "teacher" and is_dept_head)):
            if department.head and department.head != instance:
                raise serializers.ValidationError(
                    {"department_id": "Ce département a déjà un chef."}
                )
            department.head = instance
            department.save(update_fields=["head"])
        elif role == "teacher" and not is_dept_head:
            old_dept = instance.headed_department.first()
            if old_dept:
                old_dept.head = None
                old_dept.save(update_fields=["head"])
        if filiere is not None and (role == "program_manager" or (role == "teacher" and is_prog_mgr)):
            if filiere.manager and filiere.manager != instance:
                raise serializers.ValidationError(
                    {"filiere_id": "Cette filière a déjà un responsable."}
                )
            filiere.manager = instance
            filiere.save(update_fields=["manager"])
        elif role == "teacher" and not is_prog_mgr:
            old_filieres = instance.managed_filieres.all()
            for old_f in old_filieres:
                old_f.manager = None
                old_f.save(update_fields=["manager"])
        return instance

class ClasseSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()
    teacher_count = serializers.SerializerMethodField()
    filiere_id = serializers.PrimaryKeyRelatedField(
        source="filiere",
        queryset=Filiere.objects.all(),
        required=False,
        allow_null=True,
    )
    filiere_name = serializers.CharField(source="filiere.name", read_only=True)
    semestre_id = serializers.PrimaryKeyRelatedField(
        source="semestre",
        queryset=Semestre.objects.all(),
        required=False,
        allow_null=True,
    )
    semestre_name = serializers.CharField(source="semestre.name", read_only=True)
    niveau_id = serializers.CharField(source="niveau", read_only=False, required=False)
    module_id = serializers.PrimaryKeyRelatedField(
        source="module",
        queryset=Module.objects.all(),
        required=False,
        allow_null=True,
    )
    module_name = serializers.CharField(source="module.name", read_only=True)
    block_id = serializers.PrimaryKeyRelatedField(
        source="block",
        queryset=Block.objects.all(),
        required=False,
        allow_null=True,
    )
    block_name = serializers.CharField(source="block.name", read_only=True)
    room_id = serializers.PrimaryKeyRelatedField(
        source="room",
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
    )
    room_name = serializers.CharField(source="room.name", read_only=True)
    amphitheater_id = serializers.PrimaryKeyRelatedField(
        source="amphitheater",
        queryset=Amphitheater.objects.all(),
        required=False,
        allow_null=True,
    )
    amphitheater_name = serializers.CharField(source="amphitheater.name", read_only=True)
    location_display = serializers.SerializerMethodField()
    class Meta:
        model = Classe
        fields = [
            "id",
            "name",
            "code",
            "niveau_id",
            "filiere_id",
            "filiere_name",
            "semestre_id",
            "semestre_name",
            "module_id",
            "module_name",
            "academic_year",
            "location_type",
            "block_id",
            "block_name",
            "room_id",
            "room_name",
            "amphitheater_id",
            "amphitheater_name",
            "location_display",
            "student_count",
            "teacher_count",
            "level",
            "field",
            "description",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "name",
            "created_at",
            "filiere_name",
            "semestre_name",
            "module_name",
            "block_name",
            "room_name",
            "amphitheater_name",
            "location_display",
        ]
        extra_kwargs = {
            'academic_year': {'required': False},
            'code': {'required': False},
            'level': {'required': False},
            'field': {'required': False},
            'description': {'required': False},
        }

    def get_student_count(self, obj):
        if hasattr(obj, "_student_count"):
            return obj._student_count
        return obj.students.count()
    def get_teacher_count(self, obj):
        if hasattr(obj, "_teacher_count"):
            return obj._teacher_count
        return obj.teachers.count()
    def get_location_display(self, obj):
        return obj.location_display()
    def validate(self, data):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"=== ClasseSerializer.validate ===")
        logger.info(f"Input data: {data}")
        
        niveau = data.get("niveau")
        semestre = data.get("semestre")
        location_type = data.get("location_type")
        block = data.get("block")
        room = data.get("room")
        amphitheater = data.get("amphitheater")

        # Validate niveau + semestre combination
        if niveau and semestre:
            allowed = NIVEAU_SEMESTRE_MAP.get(niveau)
            if allowed is not None and semestre.name not in allowed:
                raise serializers.ValidationError(
                    f"Le niveau {niveau} ne permet que les semestres : {', '.join(sorted(allowed))}"
                )
        # Validate location type
        if location_type == "BLOC":
            if not block:
                raise serializers.ValidationError(
                    {"block_id": "Le bloc est requis pour le type 'Bloc'."}
                )
            if not room:
                raise serializers.ValidationError(
                    {"room_id": "La salle est requise pour le type 'Bloc'."}
                )
        elif location_type == "AMPHI":
            if not amphitheater:
                raise serializers.ValidationError(
                    {"amphitheater_id": "L'amphithéâtre est requis."}
                )
        elif location_type == "BOTH_ALLOWED":
            if not block or not room:
                raise serializers.ValidationError(
                    {"block_id": "Bloc et salle requis pour le type 'Les deux'."}
                )
            if not amphitheater:
                raise serializers.ValidationError(
                    {"amphitheater_id": "Amphithéâtre requis pour le type 'Les deux'."}
                )

        logger.info(f"Validation passed for ClasseSerializer")
        return data
class StudentSerializer(serializers.ModelSerializer):
    classe_name = serializers.SerializerMethodField()
    classe_field = serializers.SerializerMethodField()
    module_ids = serializers.PrimaryKeyRelatedField(
        source="modules",
        many=True,
        read_only=True,
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    module_id = serializers.IntegerField(write_only=True, required=False)
    classe = serializers.PrimaryKeyRelatedField(
        queryset=Classe.objects.all(),
        required=False,
        allow_null=True,
    )
    class Meta:
        model = Student
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "code_massar",
            "code_apogee",
            "email",
            "phone",
            "password",
            "module_id",
            "classe",
            "classe_name",
            "classe_field",
            "module_ids",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "module_ids", "user"]
    def get_classe_name(self, obj):
        return str(obj.classe)
    def get_classe_field(self, obj):
        f = obj.classe.filiere
        return f.name if f else "—"
    def validate_code_massar(self, value):
        qs = Student.objects.filter(code_massar=value)
        if self.instance and hasattr(self.instance, "pk") and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce code Massar est déjà utilisé.")
        return value

    def validate(self, data):
        module_id = data.pop("module_id", None)
        classe = data.pop("classe", None)

        if not module_id and not classe:
            raise serializers.ValidationError(
                "Un module ou une classe doit être spécifié."
            )

        if module_id:
            try:
                module = Module.objects.select_related("filiere__semestre").get(pk=module_id)
            except Module.DoesNotExist:
                raise serializers.ValidationError({"module_id": "Module introuvable."})
            filiere = module.filiere
            niveau = filiere.niveau
            semestre = filiere.semestre

            today = timezone.now()
            academic_year = f"{today.year}-{today.year + 1}"
            classe, _ = Classe.objects.get_or_create(
                filiere=filiere,
                semestre=semestre,
                niveau=niveau,
                academic_year=academic_year,
                defaults={"location_type": "BLOC"},
            )
            data["_module_id"] = module_id

        data["classe"] = classe
        return data

    def create(self, validated_data):
        module_id = validated_data.pop("_module_id", None)
        password = validated_data.pop("password", "")

        user = None
        email = validated_data.get("email", "")
        if email and password:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
                role="student",
            )
            validated_data["user"] = user

        student = super().create(validated_data)

        if module_id:
            StudentModuleEnrollment.objects.get_or_create(
                student=student, module_id=module_id
            )

        return student


class ModuleStudentSerializer(serializers.ModelSerializer):
    classe_name = serializers.SerializerMethodField()
    enrolled_at = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "first_name",
            "last_name",
            "code_massar",
            "code_apogee",
            "email",
            "phone",
            "classe_name",
            "enrolled_at",
        ]

    def get_classe_name(self, obj):
        return str(obj.classe)

    def get_enrolled_at(self, obj):
        module_id = self.context.get("module_id")
        if not module_id:
            return None
        enrollment = obj.module_enrollments.filter(module_id=module_id).first()
        return enrollment.enrolled_at if enrollment else None


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ["id", "name"]


class RoomSerializer(serializers.ModelSerializer):
    block_name = serializers.CharField(source="block.name", read_only=True)

    class Meta:
        model = Room
        fields = ["id", "name", "block_name"]


class AmphitheaterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Amphitheater
        fields = ["id", "name"]
