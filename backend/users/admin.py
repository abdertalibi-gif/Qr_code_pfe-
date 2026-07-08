from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count

from .models import (
    Amphitheater, Block, Classe, Department, Room, Student,
    StudentModuleEnrollment, User,
)


class StudentModuleEnrollmentInline(admin.TabularInline):
    model = StudentModuleEnrollment
    extra = 0
    autocomplete_fields = ["module"]


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ["name", "room_count", "amphitheater_count"]
    search_fields = ["name"]
    ordering = ["name"]

    def room_count(self, obj):
        return obj.rooms.count()
    room_count.short_description = "Salles"

    def amphitheater_count(self, obj):
        return obj.classes.filter(amphitheater__isnull=False).count()
    amphitheater_count.short_description = "Amphithéâtres"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "block", "get_status"]
    search_fields = ["name", "block__name"]
    list_filter = ["block"]
    autocomplete_fields = ["block"]

    def get_status(self, obj):
        return "Libre"
    get_status.short_description = "Status"


@admin.register(Amphitheater)
class AmphitheaterAdmin(admin.ModelAdmin):
    list_display = ["name", "capacity", "get_status"]
    search_fields = ["name"]

    def capacity(self, obj):
        return 0
    capacity.short_description = "Capacité"

    def get_status(self, obj):
        return "Libre"
    get_status.short_description = "Status"


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ["niveau", "filiere", "semestre", "academic_year", "created_at"]
    search_fields = ["filiere__name"]
    list_filter = ["niveau", "academic_year"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "first_name", "last_name", "role", "is_active"]
    list_filter = ["role", "is_active"]
    filter_horizontal = ["assigned_classes"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "role")}),
        ("Classes", {"fields": ("assigned_classes",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        "first_name",
        "last_name",
        "code_massar",
        "email",
        "phone",
        "classe",
    ]
    list_filter = ["classe"]
    search_fields = ["first_name", "last_name", "code_massar", "email", "phone"]
    inlines = [StudentModuleEnrollmentInline]


@admin.register(StudentModuleEnrollment)
class StudentModuleEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "module", "enrolled_at"]
    list_filter = ["module__filiere__semestre", "module__filiere"]
    search_fields = [
        "student__code_massar",
        "student__first_name",
        "student__last_name",
        "module__name",
    ]
    autocomplete_fields = ["student", "module"]