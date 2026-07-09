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
    IsAdminOrDepartmentHeadOrFiliereManager,
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
from .services.teacher_import import import_teachers, build_teacher_import_template_xlsx

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
        .prefetch_related("assigned_classes", "headed_department", "managed_filieres")
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
                    | Q(role="teacher", sessions__classe__filiere__department=dept)
                    | Q(role="teacher", taught_modules__filiere__department=dept)
                    | Q(role="student", student_profile__classe__department=dept)
                    | Q(role="student", student_profile__classe__filiere__department=dept)
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
                    | Q(role="teacher", taught_modules__filiere_id__in=filiere_ids)
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
            return [IsAuthenticated(), IsAdminOrDepartmentHeadOrFiliereManager()]
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
        return [IsAuthenticated(), IsAdminOrDepartmentHeadOrFiliereManager()]

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
@permission_classes([IsAuthenticated, IsAdmin])
def teacher_import_template(request):
    """Download Excel template for teacher bulk import."""
    from django.http import HttpResponse
    content = build_teacher_import_template_xlsx()
    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="teacher_import_template.xlsx"'
    return response


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
        {
            "id": t.id,
            "full_name": t.full_name,
            "email": t.email,
            "phone": t.phone,
            "cin": t.cin,
            "grade": t.grade,
            "speciality": t.speciality,
            "department_name": t.assigned_classes.first().department.name if t.assigned_classes.first() and t.assigned_classes.first().department else (t.assigned_classes.first().filiere.department.name if t.assigned_classes.first() and t.assigned_classes.first().filiere else None),
            "filiere_name": t.assigned_classes.first().filiere.name if t.assigned_classes.first() and t.assigned_classes.first().filiere else None,
            "class_count": t.assigned_classes.count(),
            "assigned_class_ids": list(t.assigned_classes.values_list("id", flat=True)),
            "is_active": t.is_active,
        }
        for t in teachers
    ]
    return Response(data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def block_list(request):
    if request.method == "POST":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"detail": "Le nom est requis."}, status=400)
        block = Block.objects.create(name=name)
        return Response({"id": block.id, "name": block.name, "rooms": []}, status=201)

    blocks = Block.objects.prefetch_related("rooms").order_by("name")
    data = []
    for b in blocks:
        data.append({
            "id": b.id,
            "name": b.name,
            "rooms": [{"id": r.id, "name": r.name} for r in b.rooms.all()],
        })
    return Response(data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def block_detail(request, pk):
    try:
        block = Block.objects.get(pk=pk)
    except Block.DoesNotExist:
        return Response({"detail": "Bloc introuvable."}, status=404)

    if request.method == "GET":
        return Response({"id": block.id, "name": block.name})

    if request.method == "PATCH":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"detail": "Le nom est requis."}, status=400)
        block.name = name
        block.save()
        return Response({"id": block.id, "name": block.name})

    if request.method == "DELETE":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        block.delete()
        return Response(status=204)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def room_list(request):
    if request.method == "POST":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        name = request.data.get("name", "").strip()
        block_id = request.data.get("block")
        if not name or not block_id:
            return Response({"detail": "Nom et bloc sont requis."}, status=400)
        try:
            block = Block.objects.get(pk=block_id)
        except Block.DoesNotExist:
            return Response({"detail": "Bloc introuvable."}, status=404)
        room = Room.objects.create(name=name, block=block)
        return Response({"id": room.id, "name": room.name, "block": block.id}, status=201)

    rooms = Room.objects.select_related("block").order_by("block__name", "name")
    data = [{"id": r.id, "name": r.name, "block": r.block_id} for r in rooms]
    return Response(data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def room_detail(request, pk):
    try:
        room = Room.objects.get(pk=pk)
    except Room.DoesNotExist:
        return Response({"detail": "Salle introuvable."}, status=404)

    if request.method == "GET":
        return Response({"id": room.id, "name": room.name, "block": room.block_id})

    if request.method == "PATCH":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        if "name" in request.data:
            name = request.data["name"].strip()
            if not name:
                return Response({"detail": "Le nom ne peut être vide."}, status=400)
            room.name = name
        if "block" in request.data:
            block_id = request.data["block"]
            try:
                room.block = Block.objects.get(pk=block_id)
            except Block.DoesNotExist:
                return Response({"detail": "Bloc introuvable."}, status=404)
        room.save()
        return Response({"id": room.id, "name": room.name, "block": room.block_id})

    if request.method == "DELETE":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        room.delete()
        return Response(status=204)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def amphitheater_list(request):
    if request.method == "POST":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"detail": "Le nom est requis."}, status=400)
        amphi = Amphitheater.objects.create(name=name)
        return Response({"id": amphi.id, "name": amphi.name}, status=201)

    amphis = Amphitheater.objects.all().order_by("name").values("id", "name")
    return Response(list(amphis))


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def amphitheater_detail(request, pk):
    try:
        amphi = Amphitheater.objects.get(pk=pk)
    except Amphitheater.DoesNotExist:
        return Response({"detail": "Amphithéâtre introuvable."}, status=404)

    if request.method == "GET":
        return Response({"id": amphi.id, "name": amphi.name})

    if request.method == "PATCH":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"detail": "Le nom est requis."}, status=400)
        amphi.name = name
        amphi.save()
        return Response({"id": amphi.id, "name": amphi.name})

    if request.method == "DELETE":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        amphi.delete()
        return Response(status=204)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def department_list(request):
    if request.method == "GET":
        depts = Department.objects.select_related("head").prefetch_related("filieres").all().order_by("name")
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
def admin_statistics(request):
    """Return attendance statistics for the admin statistics page.
    Non-admin roles only see stats scoped to their department / filieres."""
    from attendance.models import Attendance
    from courses.models import Session
    from django.db.models import Count
    from datetime import datetime, timedelta
    import math

    period_days = int(request.query_params.get("period", "30"))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)

    attend_qs = Attendance.objects.filter(
        validation_time__date__gte=start_date.date(),
        validation_time__date__lte=end_date.date(),
    )
    session_qs = Session.objects.all()
    student_qs = User.objects.filter(role="student")

    if request.user.role == "department_head":
        attend_qs = apply_role_filtering(attend_qs, "attendance", request)
        dept = get_user_department(request.user)
        if dept:
            session_qs = session_qs.filter(
                Q(classe__department=dept) | Q(classe__filiere__department=dept)
            )
            student_qs = User.objects.filter(
                role="student",
                student_profile__classe__department=dept
            ) | User.objects.filter(
                role="student",
                student_profile__classe__filiere__department=dept
            )
        else:
            session_qs = session_qs.none()
            student_qs = User.objects.none()
    elif request.user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(request.user)
        if filiere_ids:
            attend_qs = attend_qs.filter(student__classe__filiere_id__in=filiere_ids)
            session_qs = session_qs.filter(classe__filiere_id__in=filiere_ids)
            student_qs = User.objects.filter(
                role="student", student_profile__classe__filiere_id__in=filiere_ids
            )

    total_present = attend_qs.filter(attendance_status="confirmed").count()
    total_attendance = attend_qs.count()
    attendance_rate = round((total_present / total_attendance * 100) if total_attendance > 0 else 0, 1)

    active_classes = session_qs.filter(is_active=True).values("classe_id").distinct().count()
    total_students = student_qs.count()

    daily = (
        attend_qs
        .extra({"date": "date(validation_time)"})
        .values("date")
        .annotate(
            present=Count("id", filter=Q(attendance_status="confirmed")),
            total=Count("id"),
        )
        .order_by("date")
    )

    daily_data = [
        {
            "date": d["date"].isoformat() if hasattr(d["date"], "isoformat") else str(d["date"]),
            "present": d["present"],
            "total": d["total"],
        }
        for d in daily
    ]

    return Response({
        "total_present": total_present,
        "total_attendance": total_attendance,
        "attendance_rate": attendance_rate,
        "active_classes": active_classes,
        "total_students": total_students,
        "daily_attendance": daily_data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def absence_statistics(request):
    """Return comprehensive absence statistics for the Statistiques des absences tab.
    Non-admin roles see only data scoped to their department / filieres."""
    from attendance.models import Attendance
    from users.models import Student
    from courses.models import Session
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate, TruncWeek
    from datetime import datetime, timedelta

    date_from = request.query_params.get("date_from", "")
    date_to = request.query_params.get("date_to", "")
    filiere_id = request.query_params.get("filiere_id", "")
    module_id = request.query_params.get("module_id", "")
    teacher_id = request.query_params.get("teacher_id", "")
    department_id = request.query_params.get("department_id", "")
    semestre_id = request.query_params.get("semestre_id", "")
    classe_id = request.query_params.get("classe_id", "")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    if date_from:
        try:
            start_date = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            pass
    if date_to:
        try:
            end_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            pass

    qs = Attendance.objects.filter(
        validation_time__gte=start_date,
        validation_time__lt=end_date,
    )

    if filiere_id:
        qs = qs.filter(student__classe__filiere_id=filiere_id)
    if module_id:
        qs = qs.filter(session__module_id=module_id)
    if teacher_id:
        qs = qs.filter(session__teacher_id=teacher_id)
    if department_id:
        qs = qs.filter(student__classe__department_id=department_id)
    if semestre_id:
        qs = qs.filter(student__classe__semestre_id=semestre_id)
    if classe_id:
        qs = qs.filter(student__classe_id=classe_id)

    # Role-based automatic scoping (overrides query params for non-admin)
    if request.user.role == "department_head":
        dept = get_user_department(request.user)
        if dept:
            qs = qs.filter(
                Q(student__classe__department_id=dept.id)
                | Q(student__classe__filiere__department_id=dept.id)
            )
        else:
            qs = qs.none()
    elif request.user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(request.user)
        if filiere_ids:
            qs = qs.filter(student__classe__filiere_id__in=filiere_ids)
        else:
            qs = qs.none()

    total = qs.count()
    present = qs.filter(attendance_status="confirmed").count()
    absent = qs.filter(attendance_status="absent").count()
    absence_rate = round((absent / total * 100) if total > 0 else 0, 1)

    total_students = qs.values("student_id").distinct().count()
    total_sessions = qs.values("session_id").distinct().count()
    total_teachers = qs.values("session__teacher_id").distinct().count()
    total_modules = qs.values("session__module_id").distinct().count()
    total_filieres = qs.values("student__classe__filiere_id").distinct().count()
    total_departments = qs.values("student__classe__department_id").distinct().count()

    by_student = list(
        qs.values("student_id", "student__first_name", "student__last_name", "student__code_massar")
        .annotate(
            total=Count("id"),
            absent_count=Count("id", filter=Q(attendance_status="absent")),
        )
        .order_by("-absent_count")[:30]
    )
    for s in by_student:
        s["rate"] = round((s["absent_count"] / s["total"] * 100) if s["total"] > 0 else 0, 1)
        s["student_name"] = (s.get("student__first_name") or "") + " " + (s.get("student__last_name") or "")

    by_teacher = list(
        qs.values("session__teacher_id", "session__teacher__first_name", "session__teacher__last_name")
        .annotate(
            total=Count("id"),
            absent_count=Count("id", filter=Q(attendance_status="absent")),
        )
        .order_by("-absent_count")
    )
    for t in by_teacher:
        t["rate"] = round((t["absent_count"] / t["total"] * 100) if t["total"] > 0 else 0, 1)
        t["teacher_name"] = (t.get("session__teacher__first_name") or "") + " " + (t.get("session__teacher__last_name") or "")

    by_module = list(
        qs.values("session__module_id", "session__module__name")
        .annotate(
            total=Count("id"),
            absent_count=Count("id", filter=Q(attendance_status="absent")),
        )
        .order_by("-absent_count")
    )
    for m in by_module:
        m["rate"] = round((m["absent_count"] / m["total"] * 100) if m["total"] > 0 else 0, 1)
        m["module_name"] = m.get("session__module__name") or ""

    by_filiere = list(
        qs.values("student__classe__filiere_id", "student__classe__filiere__name")
        .annotate(
            total=Count("id"),
            absent_count=Count("id", filter=Q(attendance_status="absent")),
        )
        .order_by("-absent_count")
    )
    for f in by_filiere:
        f["rate"] = round((f["absent_count"] / f["total"] * 100) if f["total"] > 0 else 0, 1)
        f["filiere_name"] = f.get("student__classe__filiere__name") or ""

    by_day = list(
        qs.annotate(date=TruncDate("validation_time"))
        .values("date")
        .annotate(
            present=Count("id", filter=Q(attendance_status="confirmed")),
            absent=Count("id", filter=Q(attendance_status="absent")),
            total=Count("id"),
        )
        .order_by("date")
    )
    for d in by_day:
        d["date"] = d["date"].isoformat() if hasattr(d["date"], "isoformat") else str(d["date"])
        d["rate"] = round((d["absent"] / d["total"] * 100) if d["total"] > 0 else 0, 1)

    by_week = list(
        qs.annotate(week=TruncWeek("validation_time"))
        .values("week")
        .annotate(
            present=Count("id", filter=Q(attendance_status="confirmed")),
            absent=Count("id", filter=Q(attendance_status="absent")),
            total=Count("id"),
        )
        .order_by("week")
    )
    for w in by_week:
        w["week"] = w["week"].isoformat() if hasattr(w["week"], "isoformat") else str(w["week"])
        w["rate"] = round((w["absent"] / w["total"] * 100) if w["total"] > 0 else 0, 1)

    recent_absences = list(
        qs.filter(attendance_status="absent")
        .select_related("student", "session__teacher", "session__module")
        .order_by("-validation_time")[:50]
        .values(
            "id", "validation_time",
            "student__first_name", "student__last_name", "student__code_massar",
            "session__module__name",
            "session__teacher__first_name", "session__teacher__last_name",
            "session__date",
        )
    )
    for r in recent_absences:
        r["student"] = f"{r.pop('student__first_name', '')} {r.pop('student__last_name', '')}"
        r["module"] = r.pop("session__module__name", "")
        r["teacher"] = f"{r.pop('session__teacher__first_name', '')} {r.pop('session__teacher__last_name', '')}"
        r["date"] = r.pop("session__date", "")
        vt = r.pop("validation_time", None)
        r["time"] = vt.strftime("%H:%M:%S") if hasattr(vt, "strftime") else str(vt)[:19]

    return Response({
        "summary": {
            "total": total,
            "present": present,
            "absent": absent,
            "absence_rate": absence_rate,
            "total_students": total_students,
            "total_sessions": total_sessions,
            "total_teachers": total_teachers,
            "total_modules": total_modules,
            "total_filieres": total_filieres,
            "total_departments": total_departments,
        },
        "by_student": by_student,
        "by_teacher": by_teacher,
        "by_module": by_module,
        "by_filiere": by_filiere,
        "by_day": by_day,
        "by_week": by_week,
        "recent_absences": recent_absences,
    })
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def app_settings(request):
    """Get or save app settings (stored in cache)."""
    from django.core.cache import cache

    SETTINGS_CACHE_KEY = "app_admin_settings"

    if request.method == "POST":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        data = {
            "qr_expiry_minutes": request.data.get("qr_expiry_minutes", 20),
            "geo_radius": request.data.get("geo_radius", 50),
            "scan_limit": request.data.get("scan_limit", 1),
        }
        cache.set(SETTINGS_CACHE_KEY, data, timeout=None)
        return Response(data)

    settings = cache.get(SETTINGS_CACHE_KEY)
    if settings is None:
        settings = {
            "qr_expiry_minutes": 20,
            "geo_radius": 50,
            "scan_limit": 1,
        }
    return Response(settings)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def system_info(request):
    """Return system information for the admin settings page."""
    import django
    import sys
    import platform
    from django.db import connection

    return Response({
        "Django": django.get_version(),
        "Python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "OS": platform.system(),
        "DB Vendor": connection.vendor,
        "DB Name": connection.settings_dict.get("NAME", ""),
        "Hostname": platform.node(),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_counts(request):
    """Return all entity counts for the admin dashboard.
    Non-admin roles only see data scoped to their department / filieres."""
    from users.models import Classe, Block, Room, Amphitheater, Department
    from curriculum.models import Filiere, Module
    from courses.models import Session
    from attendance.models import Attendance

    user = request.user

    if user.role == "admin":
        return Response({
            "users": User.objects.count(),
            "admins": User.objects.filter(role="admin").count(),
            "teachers": User.objects.filter(role="teacher").count(),
            "assistants": User.objects.filter(is_also_teacher=True).count(),
            "students": User.objects.filter(role="student").count(),
            "department_heads": User.objects.filter(role="department_head").count(),
            "program_managers": User.objects.filter(role="program_manager").count(),
            "classes": Classe.objects.count(),
            "filieres": Filiere.objects.count(),
            "modules": Module.objects.count(),
            "sessions": Session.objects.count(),
            "active_sessions": Session.objects.filter(is_active=True).count(),
            "closed_sessions": Session.objects.filter(is_closed=True).count(),
            "departments": Department.objects.count(),
            "blocks": Block.objects.count(),
            "rooms": Room.objects.count(),
            "amphitheaters": Amphitheater.objects.count(),
            "attendances": Attendance.objects.count(),
            "present": Attendance.objects.filter(attendance_status="confirmed").count(),
            "absent": Attendance.objects.filter(attendance_status="absent").count(),
            "reports": Session.objects.exclude(report_file="").count(),
        })

    classes_qs = apply_role_filtering(Classe.objects.all(), "classe", request)
    filieres_qs = apply_role_filtering(Filiere.objects.all(), "filiere", request)
    modules_qs = apply_role_filtering(Module.objects.all(), "module", request)
    sessions_qs = apply_role_filtering(Session.objects.all(), "session", request)
    attendances_qs = apply_role_filtering(Attendance.objects.all(), "attendance", request)

    if user.role == "department_head":
        dept = get_user_department(user)
        if dept is None:
            users_qs = User.objects.none()
            dept_count = 0
        else:
            users_qs = User.objects.filter(
                Q(id=user.id)
                | Q(role__in=("teacher",), assigned_classes__department=dept)
                | Q(role="teacher", sessions__classe__department=dept)
                | Q(role="student", student_profile__classe__department=dept)
                | Q(role="program_manager", managed_filieres__department=dept)
            ).distinct()
            dept_count = 1
    elif user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(user)
        if not filiere_ids:
            users_qs = User.objects.none()
            dept_count = 0
        else:
            users_qs = User.objects.filter(
                Q(id=user.id)
                | Q(role__in=("teacher",), assigned_classes__filiere_id__in=filiere_ids)
                | Q(role="teacher", sessions__classe__filiere_id__in=filiere_ids)
                | Q(role="student", student_profile__classe__filiere_id__in=filiere_ids)
                | Q(role="department_head", headed_department__filieres__id__in=filiere_ids)
            ).distinct()
            dept_count = Department.objects.filter(filieres__id__in=filiere_ids).distinct().count()
    else:
        users_qs = User.objects.filter(id=user.id)
        dept_count = Department.objects.count()

    return Response({
        "users": users_qs.count(),
        "admins": users_qs.filter(role="admin").count(),
        "teachers": users_qs.filter(role="teacher").count(),
        "assistants": users_qs.filter(is_also_teacher=True).count(),
        "students": users_qs.filter(role="student").count(),
        "department_heads": users_qs.filter(role="department_head").count(),
        "program_managers": users_qs.filter(role="program_manager").count(),
        "classes": classes_qs.count(),
        "filieres": filieres_qs.count(),
        "modules": modules_qs.count(),
        "sessions": sessions_qs.count(),
        "active_sessions": sessions_qs.filter(is_active=True).count(),
        "closed_sessions": sessions_qs.filter(is_closed=True).count(),
        "departments": dept_count,
        "blocks": Block.objects.count(),
        "rooms": Room.objects.count(),
        "amphitheaters": Amphitheater.objects.count(),
        "attendances": attendances_qs.count(),
        "present": attendances_qs.filter(attendance_status="confirmed").count(),
        "absent": attendances_qs.filter(attendance_status="absent").count(),
        "reports": sessions_qs.exclude(report_file="").count(),
    })
