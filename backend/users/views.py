import logging
from typing import Type, cast

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Amphitheater, Block, Classe, Department, Room, Student, User
from .permissions import (
    IsAdmin,
    IsAdminOrTeacher,
    apply_role_filtering,
    get_user_department,
    get_user_filiere_ids,
)
from .serializers import (
    ClasseSerializer,
    DepartmentSerializer,
    LoginSerializer,
    ModuleStudentSerializer,
    StudentSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .services.student_import import (
    build_complete_import_template_xlsx,
    build_import_template_xlsx,
    import_students_complete,
    import_students_for_module,
)
from .services.teacher_import import import_teachers

logger = logging.getLogger(__name__)


class ModuleStudentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user: User = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        refresh.payload["role"] = user.role
        refresh.payload["email"] = user.email
        logger.info(f"User {user.email} logged in successfully.")
        return Response(
            {
                "message": "Login successful",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            }
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = (
        User.objects.select_related("student_profile__classe")
        .prefetch_related("assigned_classes")
        .order_by("-created_at")
    )
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self) -> Type[BaseSerializer]:
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        role_param = self.request.query_params.get("role")
        if role_param:
            qs = qs.filter(role=role_param)
        if self.request.user.role == "department_head":
            dept = get_user_department(self.request.user)
            if dept:
                qs = qs.filter(
                    Q(role="department_head", id=self.request.user.id)
                    | Q(role__in=("teacher", "admin"), assigned_classes__department=dept)
                    | Q(role="teacher", sessions__classe__department=dept)
                    | Q(role="student", student_profile__classe__department=dept)
                    | Q(role="program_manager", managed_filieres__department=dept)
                ).distinct()
            else:
                qs = qs.none()
        elif self.request.user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(self.request.user)
            if filiere_ids:
                qs = qs.filter(
                    Q(role="program_manager", id=self.request.user.id)
                    | Q(role__in=("teacher", "admin"), assigned_classes__filiere_id__in=filiere_ids)
                    | Q(role="teacher", sessions__classe__filiere_id__in=filiere_ids)
                    | Q(role="student", student_profile__classe__filiere_id__in=filiere_ids)
                ).distinct()
            else:
                qs = qs.none()
        return qs

    def get_permissions(self):
        if self.request.user.is_authenticated and self.request.user.role in ("department_head", "program_manager"):
            if self.action in ("list", "retrieve"):
                return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response(
                {"error": "Vous ne pouvez pas désactiver votre propre compte."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response(UserSerializer(user).data)


class ClasseViewSet(viewsets.ModelViewSet):
    queryset = (
        Classe.objects.select_related("block", "room", "amphitheater", "filiere", "semestre")
        .all()
        .order_by("-created_at")
    )
    serializer_class = ClasseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), IsAdminOrTeacher()]
        return super().get_permissions()

    def get_queryset(self):
        from django.db.models import Count
        qs = super().get_queryset().annotate(
            _student_count=Count("students", distinct=True),
            _teacher_count=Count("teachers", distinct=True),
        )
        user = self.request.user
        if user.role == "teacher":
            qs = qs.filter(
                Q(teachers=user) | Q(sessions__teacher=user)
            ).distinct()
        elif user.role == "department_head":
            qs = apply_role_filtering(qs, "classe", self.request)
        elif user.role == "program_manager":
            qs = apply_role_filtering(qs, "classe", self.request)
        filiere_id = self.request.query_params.get("filiere_id")
        if filiere_id:
            qs = qs.filter(filiere_id=filiere_id)
        niveau = self.request.query_params.get("niveau")
        if niveau:
            qs = qs.filter(niveau=niveau)
        semestre_id = self.request.query_params.get("semestre_id")
        if semestre_id:
            qs = qs.filter(semestre_id=semestre_id)
        module_id = self.request.query_params.get("module_id")
        if module_id:
            qs = qs.filter(module_id=module_id)
        academic_year = self.request.query_params.get("academic_year")
        if academic_year:
            qs = qs.filter(academic_year=academic_year)
        return qs

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            raise

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            raise

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            raise


class StudentViewSet(viewsets.ModelViewSet):
    queryset = (
        Student.objects.select_related("classe", "user")
        .prefetch_related("modules")
        .order_by("last_name", "first_name")
    )
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "teacher":
            qs = qs.filter(
                Q(classe__teachers=user)
                | Q(classe__sessions__teacher=user)
            ).distinct()
        elif user.role == "department_head":
            qs = apply_role_filtering(qs, "student", self.request)
        elif user.role == "program_manager":
            qs = apply_role_filtering(qs, "student", self.request)
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(code_massar__icontains=search)
                | Q(code_apogee__icontains=search)
                | Q(email__icontains=search)
            )
        classe_id = self.request.query_params.get("classe_id")
        if classe_id:
            qs = qs.filter(classe_id=classe_id)
        filiere_id = self.request.query_params.get("filiere_id")
        if filiere_id:
            qs = qs.filter(classe__filiere_id=filiere_id)
        semestre_id = self.request.query_params.get("semestre_id")
        if semestre_id:
            qs = qs.filter(classe__semestre_id=semestre_id)
        module_id = self.request.query_params.get("module_id")
        if module_id:
            qs = qs.filter(modules__id=module_id)
        return qs

    def get_permissions(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
            "import_students",
            "import_template",
            "import_complete",
            "import_complete_template",
        ):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated(), IsAdminOrTeacher()]

    @action(detail=False, methods=["get"], url_path="by-module")
    def by_module(self, request):
        module_id = request.query_params.get("module")
        if not module_id:
            return Response(
                {"detail": "Query parameter 'module' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = (
            Student.objects.filter(modules__id=module_id)
            .select_related("classe")
            .prefetch_related("module_enrollments")
            .order_by("last_name", "first_name")
            .distinct()
        )

        user = request.user
        if user.role == "department_head":
            queryset = apply_role_filtering(queryset, "student", request)
        elif user.role == "program_manager":
            queryset = apply_role_filtering(queryset, "student", request)

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(code_massar__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )

        email_filter = request.query_params.get("has_email")
        if email_filter == "yes":
            queryset = queryset.exclude(email="")
        elif email_filter == "no":
            queryset = queryset.filter(email="")

        paginator = ModuleStudentPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ModuleStudentSerializer(
            page,
            many=True,
            context={"module_id": module_id},
        )
        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_students(self, request):
        module_id = request.data.get("module_id")
        uploaded_file = request.FILES.get("file")

        if not module_id:
            return Response(
                {"detail": "module_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not uploaded_file:
            return Response(
                {"detail": "An Excel (.xlsx) or CSV file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            module_id = int(module_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "module_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report = import_students_for_module(module_id, uploaded_file)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Student import failed")
            return Response(
                {"detail": f"Import failed: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(report, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="import/template")
    def import_template(self, request):
        content = build_import_template_xlsx()
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="student_import_template.xlsx"'
        )
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="import-complete",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_complete(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"detail": "Un fichier Excel (.xlsx) est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not uploaded_file.name.lower().endswith(".xlsx"):
            return Response(
                {"detail": "Seul le format .xlsx est accepté."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report = import_students_complete(uploaded_file)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Complete student import failed")
            return Response(
                {"detail": f"Import échoué : {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(report, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="import-complete/template")
    def import_complete_template(self, request):
        content = build_complete_import_template_xlsx()
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="import_etudiants_complet.xlsx"'
        )
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = cast(User, request.user)
        user = User.objects.prefetch_related("assigned_classes").select_related(
            "student_profile__classe"
        ).get(pk=user.pk)
        return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def teacher_import_excel(request):
    from rest_framework.parsers import MultiPartParser, FormParser
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"detail": "Un fichier Excel (.xlsx) est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not uploaded_file.name.lower().endswith(".xlsx"):
            return Response(
                {"detail": "Seul le format .xlsx est accepté."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = import_teachers(uploaded_file)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Teacher import failed")
            return Response(
                {"detail": f"Import échoué : {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(report, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teacher_list(request):
    teachers = User.objects.filter(role="teacher", is_active=True).order_by("last_name", "first_name")
    if request.user.role == "department_head":
        teachers = apply_role_filtering(teachers, "teacher_list", request)
    elif request.user.role == "program_manager":
        teachers = apply_role_filtering(teachers, "teacher_list", request)
    elif request.user.role not in ("admin",):
        return Response([])
    data = [
        {"id": t.id, "full_name": t.full_name, "email": t.email}
        for t in teachers
    ]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def block_list(request):
    blocks = Block.objects.prefetch_related("rooms").order_by("name")
    data = []
    for b in blocks:
        data.append({
            "id": b.id,
            "name": b.name,
            "rooms": [{"id": r.id, "name": r.name} for r in b.rooms.all()],
        })
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def amphitheater_list(request):
    amphis = Amphitheater.objects.all().order_by("name").values("id", "name")
    return Response(list(amphis))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def department_list(request):
    if request.method == "GET":
        depts = Department.objects.select_related("head").all().order_by("name")
        user = request.user
        if user.role == "department_head":
            depts = apply_role_filtering(depts, "department", request)
        elif user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(user)
            if filiere_ids:
                depts = depts.filter(filieres__id__in=filiere_ids).distinct()
        elif user.role not in ("admin",):
            return Response([])
        serializer = DepartmentSerializer(depts, many=True)
        return Response(serializer.data)
    elif request.method == "POST":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def department_detail(request, pk):
    try:
        dept = Department.objects.select_related("head").get(pk=pk)
    except Department.DoesNotExist:
        return Response({"detail": "Département introuvable."}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if user.role not in ("admin", "department_head", "program_manager"):
        return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
    if user.role == "department_head":
        try:
            if user.headed_department.pk != dept.pk:
                return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        except Department.DoesNotExist:
            return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        serializer = DepartmentSerializer(dept)
        return Response(serializer.data)
    elif request.method in ("PUT", "PATCH"):
        if user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        partial = request.method == "PATCH"
        serializer = DepartmentSerializer(dept, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == "DELETE":
        if user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        if dept.filieres.exists():
            return Response(
                {"detail": "Impossible de supprimer ce département car des filières y sont rattachées."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dept.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_counts(request):
    """Return all entity counts for the admin dashboard."""
    from users.models import Classe, Block, Room, Amphitheater, Department
    from curriculum.models import Filiere, Module
    from courses.models import Session
    from attendance.models import Attendance

    return Response({
        "users": User.objects.count(),
        "admins": User.objects.filter(role="admin").count(),
        "teachers": User.objects.filter(role="teacher").count(),
        "students": User.objects.filter(role="student").count(),
        "department_heads": User.objects.filter(role="department_head").count(),
        "program_managers": User.objects.filter(role="program_manager").count(),
        "classes": Classe.objects.count(),
        "filieres": Filiere.objects.count(),
        "modules": Module.objects.count(),
        "sessions": Session.objects.count(),
        "departments": Department.objects.count(),
        "blocks": Block.objects.count(),
        "rooms": Room.objects.count(),
        "amphitheaters": Amphitheater.objects.count(),
        "attendances": Attendance.objects.count(),
    })
