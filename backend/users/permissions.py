from django.db.models import Q
from rest_framework.permissions import BasePermission

from .models import Department


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsAdminOrTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "teacher", "department_head", "program_manager")
        )


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "student"
        )


class IsDepartmentHead(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "department_head"
        )


class IsFiliereManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "program_manager"
        )


class IsAdminOrDepartmentHeadOrFiliereManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "teacher", "department_head", "program_manager")
        )


def get_user_department(user):
    """Return the Department for a department_head user, or None."""
    if user.role != "department_head":
        return None
    return user.headed_department.first()


def get_user_filiere_ids(user):
    """Return list of filiere IDs managed by a program_manager, or empty.
    
    Expands to ALL Filiere rows sharing the same (name, department) —
    crucial because each filiere concept (e.g. "Hygiène Info") has one
    DB row per semestre, but the manager must see ALL semestres.
    """
    if user.role != "program_manager":
        return []
    managed_ids = list(user.managed_filieres.values_list("id", flat=True))
    if not managed_ids:
        return []
    # Expand to all rows of the same filiere (same name + department)
    from curriculum.models import Filiere
    pairs = Filiere.objects.filter(id__in=managed_ids).values_list("name", "department_id")
    if not pairs:
        return managed_ids
    q = Q()
    for name, dept_id in pairs:
        q |= Q(name=name, department_id=dept_id)
    return list(Filiere.objects.filter(q).values_list("id", flat=True))


def apply_role_filtering(queryset, model_type, request):
    """
    Apply role-based filtering to any queryset.

    model_type values:
      'classe', 'student', 'user_teacher', 'user_student',
      'session', 'attendance', 'suspicious',
      'filiere', 'module',
      'teacher_list'

    Returns the filtered queryset.
    """
    user = request.user
    if not user.is_authenticated:
        return queryset.none()

    # Admin sees all
    if user.role == "admin":
        return queryset

    if user.role == "department_head":
        dept = get_user_department(user)
        if dept is None:
            return queryset.none()

        if model_type == "teacher_list":
            return queryset.filter(
                Q(assigned_classes__department=dept)
                | Q(assigned_classes__filiere__department=dept)
                | Q(sessions__classe__department=dept)
                | Q(sessions__classe__filiere__department=dept)
                | Q(taught_modules__filiere__department=dept)
            ).distinct()

        if model_type == "classe":
            return queryset.filter(
                Q(department=dept) | Q(filiere__department=dept)
            ).distinct()

        if model_type == "student":
            return queryset.filter(
                Q(classe__department=dept) | Q(classe__filiere__department=dept)
            ).distinct()

        if model_type == "user_teacher":
            return queryset.filter(
                Q(assigned_classes__department=dept)
                | Q(assigned_classes__filiere__department=dept)
                | Q(sessions__classe__department=dept)
                | Q(sessions__classe__filiere__department=dept)
                | Q(taught_modules__filiere__department=dept)
            ).distinct()

        if model_type == "user_student":
            return queryset.filter(
                Q(student_profile__classe__department=dept)
                | Q(student_profile__classe__filiere__department=dept)
            ).distinct()

        if model_type == "session":
            return queryset.filter(
                Q(classe__department=dept) | Q(classe__filiere__department=dept)
            ).distinct()

        if model_type == "attendance":
            return queryset.filter(
                Q(session__classe__department=dept)
                | Q(session__classe__filiere__department=dept)
            ).distinct()

        if model_type == "suspicious":
            return queryset.filter(
                Q(session__classe__department=dept)
                | Q(session__classe__filiere__department=dept)
            ).distinct()

        filters = {
            "filiere": {"department": dept},
            "module": {"filiere__department": dept},
            "department": {"id": dept.id},
        }
        f = filters.get(model_type)
        if f:
            return queryset.filter(**f).distinct()
        return queryset

    if user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(user)
        if not filiere_ids:
            return queryset.none()

        if model_type == "teacher_list":
            return queryset.filter(
                Q(assigned_classes__filiere_id__in=filiere_ids)
                | Q(sessions__classe__filiere_id__in=filiere_ids)
                | Q(taught_modules__filiere_id__in=filiere_ids)
            ).distinct()

        if model_type == "user_teacher":
            return queryset.filter(
                Q(assigned_classes__filiere_id__in=filiere_ids)
                | Q(sessions__classe__filiere_id__in=filiere_ids)
                | Q(taught_modules__filiere_id__in=filiere_ids)
            ).distinct()

        filters = {
            "classe": {"filiere_id__in": filiere_ids},
            "student": {"classe__filiere_id__in": filiere_ids},
            "user_student": {"student_profile__classe__filiere_id__in": filiere_ids},
            "session": {"classe__filiere_id__in": filiere_ids},
            "attendance": {"session__classe__filiere_id__in": filiere_ids},
            "suspicious": {"session__classe__filiere_id__in": filiere_ids},
            "filiere": {"id__in": filiere_ids},
            "module": {"filiere_id__in": filiere_ids},
        }
        f = filters.get(model_type)
        if f:
            return queryset.filter(**f).distinct()
        return queryset

    return queryset
