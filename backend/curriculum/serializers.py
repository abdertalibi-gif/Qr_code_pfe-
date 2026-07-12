from rest_framework import serializers
from .models import Semestre, Filiere, Module
from users.models import Department, User


class ModuleSerializer(serializers.ModelSerializer):
    """Serializer for Module - with filiere/teacher details."""
    filiere_id = serializers.PrimaryKeyRelatedField(
        source="filiere", queryset=Filiere.objects.all()
    )
    filiere_name = serializers.CharField(source="filiere.name", read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = [
            "id", "name", "code", "filiere_id", "filiere_name",
            "coefficient", "total_hours", "teacher", "teacher_name",
        ]

    def get_teacher_name(self, obj):
        if obj.teacher:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}"
        return None


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "head", "head_name"]

    def get_head_name(self, obj):
        if obj.head:
            return f"{obj.head.first_name} {obj.head.last_name}"
        return None

    def validate_head(self, value):
        if value and value.role != "department_head":
            raise serializers.ValidationError(
                "Seul un compte avec le rôle Chef de Département peut être affecté."
            )
        if value and Department.objects.filter(head=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError(
                "Ce chef de département est déjà affecté à un autre département."
            )
        return value


class FiliereSerializer(serializers.ModelSerializer):
    """Serializer for Filiere - includes nested modules."""
    modules = serializers.SerializerMethodField()
    semestre_id = serializers.PrimaryKeyRelatedField(
        source="semestre",
        queryset=Semestre.objects.all(),
        required=False,
        allow_null=True,
    )
    semestre_name = serializers.SerializerMethodField()
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )
    department_name = serializers.CharField(source="department.name", read_only=True)
    manager_id = serializers.PrimaryKeyRelatedField(
        source="manager",
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Filiere
        fields = [
            "id", "name", "niveau",
            "semestre_id", "semestre_name",
            "department_id", "department_name",
            "manager_id", "manager_name",
            "modules",
        ]

    def validate_manager_id(self, value):
        if value and value.role != "program_manager":
            raise serializers.ValidationError(
                "Seul un compte avec le rôle Responsable de Filière peut être affecté."
            )
        return value

    def get_modules(self, obj):
        return [{"id": module.id, "name": module.name} for module in obj.modules.all()]

    def get_manager_name(self, obj):
        if obj.manager:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return None

    def get_semestre_name(self, obj):
        if obj.semestre:
            return obj.semestre.name
        return ""


class SemestreSerializer(serializers.ModelSerializer):
    """Serializer for Semestre - includes nested filieres."""
    filieres = FiliereSerializer(many=True, read_only=True)

    class Meta:
        model = Semestre
        fields = ["id", "name", "filieres"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["semestre"] = representation.pop("name")
        representation["semestre_id"] = representation.pop("id")
        return representation
