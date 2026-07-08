from rest_framework import serializers
from .models import Semestre, Filiere, Module
from users.models import Department, User


class ModuleSerializer(serializers.ModelSerializer):
    """Serializer for Module - returns id and name."""
    class Meta:
        model = Module
        fields = ["id", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "head", "head_name"]

    def get_head_name(self, obj):
        if obj.head:
            return f"{obj.head.first_name} {obj.head.last_name}"
        return None


class FiliereSerializer(serializers.ModelSerializer):
    """Serializer for Filiere - includes nested modules."""
    modules = serializers.SerializerMethodField()
    semestre_id = serializers.PrimaryKeyRelatedField(
        source="semestre",
        queryset=Semestre.objects.all(),
        required=False,
        allow_null=True,
    )
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
            "semestre_id",
            "department_id", "department_name",
            "manager_id", "manager_name",
            "modules",
        ]

    def get_modules(self, obj):
        return [{"id": module.id, "name": module.name} for module in obj.modules.all()]

    def get_manager_name(self, obj):
        if obj.manager:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return None


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
