from rest_framework import serializers
from .models import Semestre, Filiere, Module


class ModuleSerializer(serializers.ModelSerializer):
    """Serializer for Module - returns id and name."""
    class Meta:
        model = Module
        fields = ["id", "name"]


class FiliereSerializer(serializers.ModelSerializer):
    """Serializer for Filiere - includes nested modules."""
    modules = serializers.SerializerMethodField()

    class Meta:
        model = Filiere
        fields = ["id", "name", "modules"]

    def get_modules(self, obj):
        return [{"id": module.id, "name": module.name} for module in obj.modules.all()]


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
