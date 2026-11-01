from django.contrib.auth import authenticate
from django.contrib.auth.backends import ModelBackend
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from curriculum.models import Filiere, Module, Semestre
from users.constants import SINGLE_FILIERE_MESSAGE, same_filiere
from users.models import NIVEAU_SEMESTRE_MAP
from users.permissions import get_user_filiere_ids
from .models import Amphitheater, Block, Classe, Department, Room, Student, StudentModuleEnrollment, User


# ── Unicité des identifiants étudiants ──────────────────────────────────────
# CIN, CNE (code Massar) et email sont trois identifiants distincts. Les
# contraintes de base de données protègent contre les courses ; ces helpers
# traduisent les violations en messages précis, champ par champ.

IDENTIFIER_CONSTRAINT_MESSAGES = {
    "uniq_student_cin": {
        "cin": "Ce CIN est déjà utilisé par un autre étudiant."
    },
    "uniq_student_user_cin": {
        "cin": "Ce CIN est déjà utilisé par un autre étudiant."
    },
    "uniq_student_profile_email_ci": {
        "email": "Cette adresse e-mail est déjà utilisée par un autre étudiant."
    },
    "uniq_student_user_email_ci": {
        "email": "Cette adresse e-mail est déjà utilisée par un autre étudiant."
    },
    "students_code_massar_key": {
        "code_massar": "Ce CNE (code Massar) est déjà utilisé par un autre étudiant."
    },
    "users_email_key": {
        "email": "Cette adresse e-mail est déjà utilisée par un autre compte."
    },
}


def _integrity_constraint_errors(exc: IntegrityError):
    """Retourne un dict {champ: message} pour une violation d'unicité connue."""
    message = str(exc).lower()
    for constraint, errors in IDENTIFIER_CONSTRAINT_MESSAGES.items():
        if constraint.lower() in message:
            return errors

    # SQLite (développement) ne nomme pas toujours la contrainte.
    if "students.cin" in message:
        return {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
    if "students.email" in message:
        return {"email": "Cette adresse e-mail est déjà utilisée par un autre étudiant."}
    if "students.code_massar" in message:
        return {"code_massar": "Ce CNE (code Massar) est déjà utilisé par un autre étudiant."}
    if "users.email" in message:
        return {"email": "Cette adresse e-mail est déjà utilisée par un autre compte."}
    return None


def _raise_integrity_error(exc: IntegrityError):
    errors = _integrity_constraint_errors(exc)
    if errors:
        raise serializers.ValidationError(errors)
    raise serializers.ValidationError(
        {"detail": "Cet enregistrement viole une contrainte d'unicité."}
    )


def _normalize_identifier_input(data):
    """Supprime les espaces et normalise l'email AVANT la validation DRF.

    Les validateurs de champ (EmailValidator notamment) s'exécutent avant
    `Serializer.validate` : sans cette étape, un email entouré d'espaces serait
    rejeté pour un simple problème de format.
    """
    if hasattr(data, "copy"):
        data = data.copy()
    if isinstance(data, dict):
        for field in ("code_massar", "code_apogee", "cin"):
            value = data.get(field)
            if isinstance(value, str):
                data[field] = value.strip()
        email = data.get("email")
        if isinstance(email, str):
            data["email"] = email.strip().lower()
    return data


class EmailBackend(ModelBackend):
    """Custom authentication backend that uses email instead of username"""
    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email:
            return None
        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
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
    department_name = serializers.CharField(
        source="department.name", read_only=True, allow_null=True
    )

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
        classe = profile.classe
        data = {
            "id": profile.id,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "code_massar": profile.code_massar,
            "code_apogee": profile.code_apogee,
            "phone": profile.phone or (obj.phone if obj else ""),
            "cin": (getattr(profile, "cin", "") or (obj.cin if obj else "") or ""),
            "classe_id": profile.classe_id,
            "classe_name": str(classe) if classe else "",
            "filiere_id": classe.filiere_id if classe else None,
            "filiere_name": classe.filiere.name if classe and classe.filiere else "",
            "semestre_id": classe.semestre_id if classe else None,
            "semestre_name": classe.semestre.name if classe and classe.semestre else "",
            "module_id": classe.module_id if classe else None,
            "module_name": classe.module.name if classe and classe.module else "",
            "niveau": classe.niveau if classe else "",
            "academic_year": classe.academic_year if classe else "",
            "created_at": profile.created_at,
        }
        # La liste complète des modules n'est utile que sur /auth/me/ : on
        # l'expose uniquement lorsque la vue le demande pour ne pas alourdir
        # les réponses des listes d'utilisateurs de l'administration.
        if self.context.get("include_modules"):
            data["modules"] = [
                {
                    "id": module.id,
                    "name": module.name,
                    "code": module.code,
                    "coefficient": module.coefficient,
                    "filiere_id": module.filiere_id,
                    "filiere_name": (
                        module.filiere.name if module.filiere else ""
                    ),
                    "semestre_id": (
                        module.filiere.semestre_id if module.filiere else None
                    ),
                    "semestre_name": (
                        module.filiere.semestre.name if module.filiere and module.filiere.semestre else ""
                    ),
                    "teacher_name": (
                        module.teacher.full_name if module.teacher_id else ""
                    ),
                }
                for module in profile.modules.select_related("teacher", "filiere__semestre").all()
            ]
        return data

    def get_managed_department(self, obj):
        dept = obj.headed_department.first()
        if dept is None:
            return None
        return {"id": dept.id, "name": dept.name}

    def get_managed_filieres(self, obj):
        return [
            {"id": f.id, "name": f.name, "semestre": f.semestre_id}
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
            "phone",
            "cin",
            "grade",
            "speciality",
            "is_also_teacher",
            "is_department_head",
            "is_program_manager",
        ]

    def to_internal_value(self, data):
        return super().to_internal_value(_normalize_identifier_input(data))

    def validate(self, data):
        password = data.get("password")
        password_confirm = data.get("password_confirm")
        if password_confirm is not None and password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        data.pop("password_confirm", None)
        role = data.get("role") or (getattr(self.instance, "role", None) if self.instance else None) or "teacher"
        email = (data.get("email") or "").strip().lower()
        if email:
            data["email"] = email
            if role == "student":
                if not email.endswith("@edu.umi.ac.ma"):
                    raise serializers.ValidationError({"email": "L'email étudiant doit être @edu.umi.ac.ma."})
            elif not email.endswith("@umi.ac.ma"):
                raise serializers.ValidationError({"email": "L'email doit être @umi.ac.ma."})
        cin = (data.get("cin") or "").strip()
        if "cin" in data:
            data["cin"] = cin

        if email:
            duplicate = User.objects.filter(email__iexact=email)
            if self.instance is not None:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"email": "Cette adresse e-mail est déjà utilisée par un autre compte."}
                )

        if role == "student":
            if email and Student.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError(
                    {"email": "Un profil étudiant utilise déjà cette adresse e-mail."}
                )
            if cin:
                if User.objects.filter(role="student", cin__iexact=cin).exists():
                    raise serializers.ValidationError(
                        {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                    )
                if Student.objects.filter(cin__iexact=cin).exists():
                    raise serializers.ValidationError(
                        {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                    )

        assigned = data.get("assigned_classes", [])
        can_have_classes = ("teacher", "department_head", "program_manager")
        if role not in can_have_classes and assigned:
            raise serializers.ValidationError(
                {"assigned_class_ids": "Seuls les enseignants, chefs de département et responsables de filière peuvent avoir des classes."}
            )
        department = data.get("department")
        filiere = data.get("filiere")
        if role == "department_head" and not department:
            raise serializers.ValidationError(
                {"department_id": "Le département est obligatoire pour le chef de département."}
            )
        if role == "program_manager" and not filiere:
            raise serializers.ValidationError(
                {"filiere_id": "La filière est obligatoire pour le responsable de filière."}
            )
        if role == "teacher" and not department:
            raise serializers.ValidationError(
                {"department_id": "Le département est obligatoire pour l'enseignant."}
            )
        if role != "teacher":
            data.pop("is_also_teacher", None)
        return data

    def create(self, validated_data):
        role = validated_data.get("role", "teacher")
        assigned_classes = validated_data.pop("assigned_classes", [])
        department = validated_data.pop("department", None)
        filiere = validated_data.pop("filiere", None)
        validated_data.pop("is_department_head", None)
        validated_data.pop("is_program_manager", None)
        password = validated_data.pop("password")
        user = User(**validated_data)
        if department and role in ("teacher", "department_head"):
            user.department = department
        user.set_password(password)
        try:
            user.save()
        except IntegrityError as exc:
            _raise_integrity_error(exc)
        if role == "teacher":
            if assigned_classes:
                user.assigned_classes.set(assigned_classes)
        elif assigned_classes:
            user.assigned_classes.set(assigned_classes)
        if department and role == "department_head":
            if department.head and department.head != user:
                raise serializers.ValidationError(
                    {"department_id": "Ce département a déjà un chef."}
                )
            department.head = user
            department.save(update_fields=["head"])
        if filiere and role == "program_manager":
            from curriculum.models import Filiere as FiliereModel
            same_filieres = FiliereModel.objects.filter(name=filiere.name, department=filiere.department)
            conflicting = same_filieres.exclude(manager=user).exclude(manager__isnull=True)
            if conflicting.exists():
                other = conflicting.first()
                msg = "Cette filière a déjà un responsable (%s)." % other.manager.get_full_name()
                raise serializers.ValidationError({"filiere_id": msg})
            same_filieres.update(manager=user)
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
            "phone",
            "cin",
            "grade",
            "speciality",
            "is_also_teacher",
            "is_department_head",
            "is_program_manager",
        ]

    def to_internal_value(self, data):
        return super().to_internal_value(_normalize_identifier_input(data))

    def validate(self, data):
        role = data.get("role", getattr(self.instance, "role", None))
        email = (data.get("email") or "").strip().lower()
        if email:
            data["email"] = email
        if email and role:
            if role == "student":
                if not email.endswith("@edu.umi.ac.ma"):
                    raise serializers.ValidationError({"email": "L'email étudiant doit être @edu.umi.ac.ma."})
            elif not email.endswith("@umi.ac.ma"):
                raise serializers.ValidationError({"email": "L'email doit être @umi.ac.ma."})
        cin = (data.get("cin") or "").strip()
        if "cin" in data:
            data["cin"] = cin

        instance = self.instance
        profile = None
        if instance is not None and instance.role == "student":
            try:
                profile = instance.student_profile
            except Student.DoesNotExist:
                profile = None

        if email:
            duplicate = User.objects.filter(email__iexact=email)
            if instance is not None:
                duplicate = duplicate.exclude(pk=instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"email": "Cette adresse e-mail est déjà utilisée par un autre compte."}
                )

        if role == "student":
            if email:
                duplicate_profile = Student.objects.filter(email__iexact=email)
                if profile is not None:
                    duplicate_profile = duplicate_profile.exclude(pk=profile.pk)
                if duplicate_profile.exists():
                    raise serializers.ValidationError(
                        {"email": "Cette adresse e-mail est déjà utilisée par un autre étudiant."}
                    )
            if cin:
                duplicate_cin = User.objects.filter(role="student", cin__iexact=cin)
                if instance is not None:
                    duplicate_cin = duplicate_cin.exclude(pk=instance.pk)
                if duplicate_cin.exists():
                    raise serializers.ValidationError(
                        {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                    )
                duplicate_student_cin = Student.objects.filter(cin__iexact=cin)
                if profile is not None:
                    duplicate_student_cin = duplicate_student_cin.exclude(pk=profile.pk)
                if duplicate_student_cin.exists():
                    raise serializers.ValidationError(
                        {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                    )

        assigned = data.get("assigned_classes")
        can_have_classes = ("teacher", "department_head", "program_manager")
        if assigned is not None and role not in can_have_classes and assigned:
            raise serializers.ValidationError(
                {"assigned_class_ids": "Seuls les enseignants, chefs de département et responsables de filière peuvent avoir des classes."}
            )
        if role == "teacher" and "department" in data and not data.get("department") and not self.instance:
            raise serializers.ValidationError(
                {"department_id": "Le département est obligatoire pour l'enseignant."}
            )
        if role != "teacher":
            data.pop("is_also_teacher", None)
        return data

    def update(self, instance, validated_data):
        assigned_classes = validated_data.pop("assigned_classes", None)
        department_missing = object()
        department = validated_data.pop("department", department_missing)
        filiere = validated_data.pop("filiere", None)
        validated_data.pop("is_department_head", None)
        validated_data.pop("is_program_manager", None)
        password = validated_data.pop("password", None)
        role = validated_data.get("role", instance.role)
        old_role = instance.role
        if department is not department_missing and role in ("teacher", "department_head"):
            instance.department = department
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        try:
            instance.save()
        except IntegrityError as exc:
            _raise_integrity_error(exc)

        # Garder la fiche étudiant alignée sur les identifiants du compte.
        if instance.role == "student":
            try:
                profile = instance.student_profile
            except Student.DoesNotExist:
                profile = None
            if profile is not None:
                profile_updates = []
                if "email" in validated_data and profile.email != (instance.email or ""):
                    profile.email = instance.email
                    profile_updates.append("email")
                if "cin" in validated_data and profile.cin != (instance.cin or ""):
                    profile.cin = instance.cin or ""
                    profile_updates.append("cin")
                if profile_updates:
                    try:
                        profile.save(update_fields=profile_updates)
                    except IntegrityError as exc:
                        _raise_integrity_error(exc)

        if role == "teacher":
            if assigned_classes is not None:
                instance.assigned_classes.set(assigned_classes)
        elif assigned_classes is not None:
            instance.assigned_classes.set(assigned_classes)
        if department is not department_missing and department is not None and role == "department_head":
            if department.head and department.head != instance:
                raise serializers.ValidationError(
                    {"department_id": "Ce département a déjà un chef."}
                )
            department.head = instance
            department.save(update_fields=["head"])
        elif old_role == "department_head" and role != "department_head":
            old_dept = instance.headed_department.first()
            if old_dept:
                old_dept.head = None
                old_dept.save(update_fields=["head"])
        if filiere is not None and role == "program_manager":
            from curriculum.models import Filiere as FiliereModel
            same_filieres = FiliereModel.objects.filter(name=filiere.name, department=filiere.department)
            conflicting = same_filieres.exclude(manager=instance).exclude(manager__isnull=True)
            if conflicting.exists():
                other = conflicting.first()
                msg = "Cette filière a déjà un responsable (%s)." % other.manager.get_full_name()
                raise serializers.ValidationError({"filiere_id": msg})
            same_filieres.update(manager=instance)
        elif old_role == "program_manager" and role != "program_manager":
            from curriculum.models import Filiere as FiliereModel
            old_filieres = instance.managed_filieres.all()
            old_pairs = set(old_filieres.values_list("name", "department_id"))
            for name, dept_id in old_pairs:
                FiliereModel.objects.filter(name=name, department_id=dept_id).update(manager=None)
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
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="teacher"),
        required=False, allow_null=True, write_only=True,
    )
    teacher_name = serializers.SerializerMethodField()
    assigned_teacher_id = serializers.SerializerMethodField()
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )
    department_name = serializers.CharField(source="department.name", read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user and user.is_authenticated and user.role == "department_head":
            dept = user.headed_department.first()
            if dept:
                dept_filieres = Filiere.objects.filter(department=dept)
                dept_module_ids = Module.objects.filter(filiere__department=dept).values_list("id", flat=True)
                dept_teacher_ids = User.objects.filter(
                    Q(role="teacher")
                    & (Q(department=dept)
                       | Q(assigned_classes__department=dept)
                       | Q(assigned_classes__filiere__department=dept)
                       | Q(sessions__classe__department=dept)
                       | Q(sessions__classe__filiere__department=dept)
                       | Q(taught_modules__filiere__department=dept))
                ).values_list("id", flat=True).distinct()
                self.fields["filiere_id"].queryset = dept_filieres
                self.fields["module_id"].queryset = Module.objects.filter(id__in=dept_module_ids)
                self.fields["semestre_id"].queryset = Semestre.objects.filter(filieres__department=dept).distinct()
                self.fields["teacher_id"].queryset = User.objects.filter(id__in=list(dept_teacher_ids))
        if user and user.is_authenticated and user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(user)
            if filiere_ids:
                pm_filieres = Filiere.objects.filter(id__in=filiere_ids)
                pm_module_ids = Module.objects.filter(filiere_id__in=filiere_ids).values_list("id", flat=True)
                pm_teacher_ids = User.objects.filter(
                    Q(role="teacher")
                    & (Q(assigned_classes__filiere_id__in=filiere_ids)
                       | Q(sessions__classe__filiere_id__in=filiere_ids)
                       | Q(taught_modules__filiere_id__in=filiere_ids))
                ).values_list("id", flat=True).distinct()
                self.fields["filiere_id"].queryset = pm_filieres
                self.fields["module_id"].queryset = Module.objects.filter(id__in=list(pm_module_ids))
                self.fields["semestre_id"].queryset = Semestre.objects.filter(filieres__id__in=filiere_ids).distinct()
                self.fields["teacher_id"].queryset = User.objects.filter(id__in=list(pm_teacher_ids))

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
            "teacher_id",
            "teacher_name",
            "assigned_teacher_id",
            "department_id",
            "department_name",
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
            "teacher_name",
            "assigned_teacher_id",
            "department_name",
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
    def get_teacher_name(self, obj):
        teachers = getattr(obj, "first_teacher", None)
        if teachers is not None:
            if teachers:
                return teachers[0].full_name
            return None
        teacher = obj.teachers.first()
        if teacher:
            return teacher.full_name
        return None
    def get_assigned_teacher_id(self, obj):
        teachers = getattr(obj, "first_teacher", None)
        if teachers is not None:
            return teachers[0].pk if teachers else None
        teacher = obj.teachers.first()
        return teacher.pk if teacher else None
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

        # Validate uniqueness — matches the DB constraint unique_classe_per_module_year
        filiere = data.get("filiere")
        module = data.get("module")
        academic_year = data.get("academic_year")
        if niveau and semestre and filiere and academic_year:
            qs = Classe.objects.filter(
                niveau=niveau,
                semestre=semestre,
                filiere=filiere,
                academic_year=academic_year,
            )
            if module:
                qs = qs.filter(module=module)
            else:
                qs = qs.filter(module__isnull=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": ["Une classe avec ces paramètres existe déjà pour cette année universitaire."]}
                )

        logger.info(f"Validation passed for ClasseSerializer")
        return data

    def create(self, validated_data):
        teacher = validated_data.pop("teacher_id", None)
        instance = super().create(validated_data)
        if teacher:
            teacher.assigned_classes.add(instance)
        return instance

    def update(self, instance, validated_data):
        teacher_provided = "teacher_id" in validated_data
        teacher = validated_data.pop("teacher_id", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if teacher_provided:
            # L'enseignant de la classe est l'unique source de vérité :
            # remplacer l'affectation (retire l'ancien enseignant, ajoute le nouveau).
            instance.teachers.set([teacher] if teacher else [])
        return instance

class StudentSerializer(serializers.ModelSerializer):
    classe_name = serializers.SerializerMethodField()
    classe_field = serializers.SerializerMethodField()
    filiere_name = serializers.SerializerMethodField()
    semestre_name = serializers.SerializerMethodField()
    niveau = serializers.SerializerMethodField()
    module_ids = serializers.PrimaryKeyRelatedField(
        source="modules",
        many=True,
        read_only=True,
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    module_id = serializers.IntegerField(write_only=True, required=False)
    # Déclaré explicitement pour maîtriser le message d'erreur d'unicité.
    code_massar = serializers.CharField(required=False, allow_blank=True)
    # Ces champs sont validés dans `validate()` : un étudiant existant peut
    # être réutilisé avec ses identifiants, sans déclencher le validateur
    # d'unicité automatique du modèle (qui ne connaît pas la réutilisation).
    cin = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    email = serializers.EmailField(required=False, allow_blank=True)
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
            "cin",
            "email",
            "phone",
            "password",
            "module_id",
            "classe",
            "classe_name",
            "classe_field",
            "filiere_name",
            "semestre_name",
            "niveau",
            "module_ids",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "module_ids", "user"]

    def get_classe_name(self, obj):
        return str(obj.classe)

    def get_classe_field(self, obj):
        f = obj.classe.filiere
        return f.name if f else "—"

    def get_filiere_name(self, obj):
        return obj.classe.filiere.name if obj.classe and obj.classe.filiere else "—"

    def get_semestre_name(self, obj):
        return obj.classe.semestre.name if obj.classe and obj.classe.semestre else "—"

    def get_niveau(self, obj):
        return obj.classe.niveau if obj.classe else "—"

    def to_internal_value(self, data):
        return super().to_internal_value(_normalize_identifier_input(data))

    def _current_value(self, data, field):
        if field in data:
            return data.get(field) or ""
        if self.instance is not None:
            return getattr(self.instance, field, "") or ""
        return ""

    def validate(self, data):
        module_id = data.pop("module_id", None)
        classe_provided = "classe" in data
        classe = data.pop("classe", None)

        code = self._current_value(data, "code_massar").strip()
        email = self._current_value(data, "email").strip().lower()
        cin = self._current_value(data, "cin").strip()

        if "code_massar" in data or self.instance is None:
            data["code_massar"] = code
        if "email" in data or self.instance is None:
            data["email"] = email
        if "cin" in data or self.instance is None:
            data["cin"] = cin

        if not code:
            raise serializers.ValidationError(
                {"code_massar": "Le CNE (code Massar) est obligatoire."}
            )
        if email and not email.endswith("@edu.umi.ac.ma"):
            raise serializers.ValidationError(
                {"email": "L'email étudiant doit être @edu.umi.ac.ma."}
            )

        if self.instance is None and not module_id and not classe:
            raise serializers.ValidationError(
                "Un module ou une classe doit être spécifié."
            )

        # Les trois identifiants sont distincts et doivent rester uniques.
        by_code = (
            Student.objects.filter(code_massar__iexact=code).first()
            if code
            else None
        )
        by_email = (
            Student.objects.filter(email__iexact=email).first()
            if email
            else None
        )
        target = self.instance or by_code or by_email

        if by_code and by_email and by_code.pk != by_email.pk:
            raise serializers.ValidationError(
                {
                    "code_massar": (
                        "Ce CNE (code Massar) et cette adresse e-mail "
                        "appartiennent à deux étudiants différents."
                    )
                }
            )

        if by_code and target and by_code.pk != target.pk:
            raise serializers.ValidationError(
                {
                    "code_massar": (
                        "Ce CNE (code Massar) est déjà utilisé par "
                        f"{by_code.first_name} {by_code.last_name}."
                    )
                }
            )

        if by_email and target and by_email.pk != target.pk:
            raise serializers.ValidationError(
                {
                    "email": (
                        "Cette adresse e-mail est déjà utilisée par "
                        f"{by_email.first_name} {by_email.last_name}."
                    )
                }
            )

        if email:
            user_owner = User.objects.filter(email__iexact=email).first()
            if user_owner and (target is None or user_owner.pk != target.user_id):
                try:
                    owner_profile = user_owner.student_profile
                except Student.DoesNotExist:
                    owner_profile = None
                reusable_account = (
                    target is not None
                    and target.user_id is None
                    and user_owner.role == "student"
                    and owner_profile is None
                )
                if not reusable_account:
                    label = (
                        f"{owner_profile.first_name} {owner_profile.last_name}"
                        if owner_profile is not None
                        else "un autre compte"
                    )
                    raise serializers.ValidationError(
                        {
                            "email": (
                                "Cette adresse e-mail est déjà utilisée par "
                                f"{label}."
                            )
                        }
                    )

        if cin:
            cin_owner = (
                Student.objects.filter(cin__iexact=cin).first()
            )
            if cin_owner and (target is None or cin_owner.pk != target.pk):
                raise serializers.ValidationError(
                    {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                )
            user_cin_owner = User.objects.filter(
                role="student", cin__iexact=cin
            ).first()
            if user_cin_owner and (
                target is None or user_cin_owner.pk != target.user_id
            ):
                raise serializers.ValidationError(
                    {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                )

        # Lorsqu'un étudiant existant est réutilisé (ajout à un module), ses
        # identifiants ne doivent jamais être remplacés automatiquement.
        if target is not None and self.instance is None:
            if (
                by_code is not None
                and by_code.email
                and email
                and by_code.email.strip().lower() != email
            ):
                raise serializers.ValidationError(
                    {
                        "code_massar": (
                            "Ce CNE (code Massar) est déjà utilisé par "
                            f"{by_code.first_name} {by_code.last_name}."
                        )
                    }
                )
            if (
                by_email is not None
                and by_email.code_massar
                and code
                and by_email.code_massar.strip().lower() != code.lower()
            ):
                raise serializers.ValidationError(
                    {
                        "email": (
                            "Cette adresse e-mail est déjà utilisée par "
                            f"{by_email.first_name} {by_email.last_name}."
                        )
                    }
                )
            if (
                target.cin
                and cin
                and target.cin.strip().lower() != cin.lower()
            ):
                raise serializers.ValidationError(
                    {
                        "cin": (
                            "Ce CIN ne correspond pas à l'étudiant associé "
                            "à ce CNE / cette adresse e-mail."
                        )
                    }
                )

        if module_id:
            try:
                module = Module.objects.select_related("filiere__semestre").get(pk=module_id)
            except Module.DoesNotExist:
                raise serializers.ValidationError({"module_id": "Module introuvable."})
            filiere = module.filiere
            niveau = filiere.niveau
            semestre = filiere.semestre

            # Une seule filière par étudiant : la nouvelle inscription doit
            # rester dans la filière de sa classe actuelle, quel que soit le
            # semestre du module (S1 à S6 autorisés).
            existing = self.instance or target
            if (
                existing is not None
                and existing.classe_id
                and not same_filiere(existing.classe.filiere, filiere)
            ):
                raise serializers.ValidationError(
                    {"module_id": SINGLE_FILIERE_MESSAGE}
                )

            today = timezone.now()
            academic_year = f"{today.year}-{today.year + 1}"
            # Priorité à la classe déjà liée à ce module ; sinon une classe
            # générique de la même filière/semestre/année ; sinon création.
            classe = (
                Classe.objects.filter(module=module).order_by("id").first()
                or Classe.objects.filter(
                    filiere=filiere,
                    semestre=semestre,
                    niveau=niveau,
                    academic_year=academic_year,
                )
                .order_by("id")
                .first()
                or Classe.objects.create(
                    filiere=filiere,
                    semestre=semestre,
                    module=module,
                    niveau=niveau,
                    academic_year=academic_year,
                    location_type="BLOC",
                )
            )
            data["_module_id"] = module_id

        if classe_provided or module_id or self.instance is None:
            data["classe"] = classe

        # Une réaffectation de classe ne doit pas faire changer de filière :
        # la filière d'inscription de l'étudiant reste unique et permanente.
        final_classe = data.get("classe")
        if (
            final_classe is not None
            and target is not None
            and target.classe_id
            and not same_filiere(target.classe.filiere, final_classe.filiere)
        ):
            raise serializers.ValidationError(
                {"classe": SINGLE_FILIERE_MESSAGE}
            )
        return data

    def _existing_student(self, code, email):
        """Retrouve un étudiant par CNE, puis par email (jamais de doublon)."""
        student = None
        if code:
            student = (
                Student.objects.select_related("user")
                .filter(code_massar__iexact=code)
                .first()
            )
        if student is None and email:
            student = (
                Student.objects.select_related("user")
                .filter(email__iexact=email)
                .first()
            )
        return student

    def create(self, validated_data):
        module_id = validated_data.pop("_module_id", None)
        password = validated_data.pop("password", "")

        email = validated_data.get("email", "")
        code_massar = validated_data.get("code_massar", "")
        cin = validated_data.get("cin", "")

        existing_student = self._existing_student(code_massar, email)

        if existing_student:
            if module_id:
                module_filiere = (
                    Module.objects.filter(pk=module_id)
                    .select_related("filiere")
                    .first()
                )
                if (
                    module_filiere is not None
                    and existing_student.classe_id
                    and not same_filiere(
                        existing_student.classe.filiere,
                        module_filiere.filiere,
                    )
                ):
                    raise serializers.ValidationError(
                        {"module_id": SINGLE_FILIERE_MESSAGE}
                    )

            if module_id and StudentModuleEnrollment.objects.filter(
                student=existing_student, module_id=module_id
            ).exists():
                raise serializers.ValidationError(
                    "Cet étudiant est déjà inscrit dans ce module."
                )

            # Le compte et les identifiants (CIN, CNE, email) sont permanents.
            # Une nouvelle inscription à un module d'une autre filière ou d'un
            # autre semestre ne crée jamais un second étudiant : seuls les
            # champs non identifiants et la classe courante sont actualisés.
            for attr in ("first_name", "last_name", "phone", "classe"):
                val = validated_data.get(attr)
                if val is not None:
                    setattr(existing_student, attr, val)
            if not existing_student.email and email:
                existing_student.email = email
            if not existing_student.cin and cin:
                existing_student.cin = cin

            user = existing_student.user
            if user is None and email:
                user = User.objects.filter(email__iexact=email).first()
                if user is not None:
                    if user.role != "student":
                        raise serializers.ValidationError(
                            {"email": "Cette adresse e-mail appartient à un compte non étudiant."}
                        )
                    try:
                        profile = user.student_profile
                    except Student.DoesNotExist:
                        profile = None
                    if profile is not None and profile.pk != existing_student.pk:
                        raise serializers.ValidationError(
                            {"email": "Cette adresse e-mail est déjà liée à un autre étudiant."}
                        )
                elif password:
                    try:
                        user = User.objects.create_user(
                            email=email,
                            password=password,
                            first_name=validated_data.get("first_name", ""),
                            last_name=validated_data.get("last_name", ""),
                            role="student",
                            phone=validated_data.get("phone", "") or "",
                            cin=cin or "",
                        )
                    except IntegrityError as exc:
                        _raise_integrity_error(exc)
                if user is not None:
                    existing_student.user = user

            try:
                with transaction.atomic():
                    existing_student.save()
                    if module_id:
                        StudentModuleEnrollment.objects.create(
                            student=existing_student, module_id=module_id
                        )
            except IntegrityError as exc:
                _raise_integrity_error(exc)

            return existing_student

        # Aucun profil existant : réutiliser un compte étudiant libre, sinon
        # en créer un seul (jamais de second compte pour les mêmes identifiants).
        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if user is not None:
                if user.role != "student":
                    raise serializers.ValidationError(
                        {"email": "Cette adresse e-mail appartient à un compte non étudiant."}
                    )
                try:
                    profile = user.student_profile
                except Student.DoesNotExist:
                    profile = None
                if profile is not None:
                    raise serializers.ValidationError(
                        {"email": "Cette adresse e-mail est déjà liée à un étudiant."}
                    )
            elif password:
                try:
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        first_name=validated_data.get("first_name", ""),
                        last_name=validated_data.get("last_name", ""),
                        role="student",
                        phone=validated_data.get("phone", "") or "",
                        cin=cin or "",
                    )
                except IntegrityError as exc:
                    _raise_integrity_error(exc)

        if user is not None:
            if cin and not user.cin:
                user.cin = cin
                try:
                    user.save(update_fields=["cin"])
                except IntegrityError as exc:
                    _raise_integrity_error(exc)
            validated_data["user"] = user

        try:
            with transaction.atomic():
                student = super().create(validated_data)
                if module_id:
                    StudentModuleEnrollment.objects.create(
                        student=student, module_id=module_id
                    )
        except IntegrityError as exc:
            _raise_integrity_error(exc)

        return student

    def update(self, instance, validated_data):
        cin_provided = "cin" in validated_data
        cin = validated_data.get("cin")
        email = validated_data.get("email")

        try:
            with transaction.atomic():
                student = super().update(instance, validated_data)

                user = student.user
                if user is not None:
                    updates = []
                    if cin_provided and (user.cin or "") != (cin or ""):
                        user.cin = cin or ""
                        updates.append("cin")
                    phone = validated_data.get("phone")
                    if phone is not None and (user.phone or "") != phone:
                        user.phone = phone
                        updates.append("phone")
                    if email and user.email.lower() != email.lower():
                        user.email = email
                        updates.append("email")
                    if updates:
                        user.save(update_fields=updates)
        except IntegrityError as exc:
            _raise_integrity_error(exc)

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
