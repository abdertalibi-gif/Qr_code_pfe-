import logging
from typing import Type, cast

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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
        department_id = self.request.query_params.get("department_id")
        if department_id and role_param == "program_manager":
            qs = qs.filter(managed_filieres__department_id=department_id).distinct()
        if self.request.user.role == "department_head":
            dept = get_user_department(self.request.user)
            if dept:
                qs = qs.filter(
                    Q(role="department_head", id=self.request.user.id)
                    | Q(role__in=("teacher", "admin"),
                        assigned_classes__department=dept)
                    | Q(role__in=("teacher", "admin"),
                        assigned_classes__filiere__department=dept)
                    | Q(role__in=("teacher", "admin"),
                        sessions__classe__department=dept)
                    | Q(role__in=("teacher", "admin"),
                        sessions__classe__filiere__department=dept)
                    | Q(role__in=("teacher", "admin"),
                        taught_modules__filiere__department=dept)
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

    def perform_destroy(self, instance):
        if self.request.user == instance:
            raise ValidationError("Vous ne pouvez pas supprimer votre propre compte.")
        if instance.is_superuser:
            raise ValidationError("Impossible de supprimer un superutilisateur.")
        protected = ["admin@fs.umi.ac.ma", "admin@umi.ac.ma"]
        if instance.email and instance.email.lower() in protected:
            raise ValidationError("Ce compte administrateur ne peut pas être supprimé.")
        instance.delete()

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
        if self.action in ("list", "retrieve", "create"):
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
            qs = qs.filter(teachers=user).distinct()
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

    def perform_create(self, serializer):
        user = self.request.user
        filiere = serializer.validated_data.get("filiere")
        teacher_id = self.request.data.get("teacher_id")
        if user.role == "department_head":
            dept = get_user_department(user)
            if filiere and dept and filiere.department_id != dept.id:
                from rest_framework import serializers as rf_serializers
                raise rf_serializers.ValidationError(
                    {"filiere": "Vous ne pouvez créer une classe que dans votre département."}
                )
            if teacher_id:
                from users.models import User
                teacher = User.objects.filter(pk=teacher_id).first()
                if teacher and not teacher.assigned_classes.filter(
                    Q(department=dept) | Q(filiere__department=dept)
                ).exists() and not teacher.sessions.filter(
                    Q(classe__department=dept) | Q(classe__filiere__department=dept)
                ).exists() and not teacher.taught_modules.filter(
                    Q(filiere__department=dept)
                ).exists():
                    from rest_framework import serializers as rf_serializers
                    raise rf_serializers.ValidationError(
                        {"teacher_id": "Cet enseignant n'appartient pas à votre département."}
                    )
        elif user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(user)
            if filiere and filiere_ids and filiere.id not in filiere_ids:
                from rest_framework import serializers as rf_serializers
                raise rf_serializers.ValidationError(
                    {"filiere": "Vous ne pouvez créer une classe que dans votre filière."}
                )
            if teacher_id and filiere_ids:
                from users.models import User
                teacher = User.objects.filter(pk=teacher_id).first()
                if teacher and not teacher.assigned_classes.filter(
                    filiere_id__in=filiere_ids
                ).exists() and not teacher.sessions.filter(
                    classe__filiere_id__in=filiere_ids
                ).exists() and not teacher.taught_modules.filter(
                    filiere_id__in=filiere_ids
                ).exists():
                    from rest_framework import serializers as rf_serializers
                    raise rf_serializers.ValidationError(
                        {"teacher_id": "Cet enseignant n'appartient pas à votre filière."}
                    )
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        filiere = serializer.validated_data.get("filiere")
        if user.role == "department_head":
            dept = get_user_department(user)
            if filiere and dept and filiere.department_id != dept.id:
                from rest_framework import serializers as rf_serializers
                raise rf_serializers.ValidationError(
                    {"filiere": "Vous ne pouvez modifier une classe que dans votre département."}
                )
        if user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(user)
            if filiere and filiere_ids and filiere.id not in filiere_ids:
                from rest_framework import serializers as rf_serializers
                raise rf_serializers.ValidationError(
                    {"filiere": "Vous ne pouvez modifier une classe que dans votre filière."}
                )
        serializer.save()


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
            qs = qs.filter(classe__teachers=user).distinct()
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
        niveau = self.request.query_params.get("niveau")
        if niveau:
            qs = qs.filter(classe__niveau=niveau)
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
        logger.info("Teacher import started: %s (%d bytes)", uploaded_file.name, uploaded_file.size)
        try:
            report = import_teachers(uploaded_file)
            logger.info(
                "Teacher import finished: %d created, %d updated, %d errors",
                report.get("imported", 0),
                report.get("updated", 0),
                len(report.get("errors", [])),
            )
        except ValueError as exc:
            logger.warning("Teacher import value error: %s", exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Teacher import failed unexpectedly")
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
    user = request.user

    teachers = User.objects.filter(role="teacher", is_active=True).prefetch_related(
        Prefetch("assigned_classes", queryset=Classe.objects.select_related("department", "filiere__department"))
    ).order_by("last_name", "first_name")

    if user.role == "department_head":
        teachers = apply_role_filtering(teachers, "teacher_list", request)
    elif user.role == "program_manager":
        teachers = apply_role_filtering(teachers, "teacher_list", request)
    elif user.role not in ("admin",):
        return Response([])

    classe_id = request.query_params.get("classe_id", "")
    if classe_id:
        teachers = teachers.filter(
            Q(assigned_classes__id=classe_id) | Q(sessions__classe_id=classe_id)
        ).distinct()

    data = []
    for t in teachers:
        ac = list(t.assigned_classes.all())
        departments = sorted(set(
            c.department.name for c in ac if c.department and c.department.name
        ))
        if not departments:
            departments = sorted(set(
                c.filiere.department.name for c in ac
                if c.filiere and c.filiere.department and c.filiere.department.name
            ))
        dept_name = departments[0] if departments else None
        data.append({
            "id": t.id,
            "full_name": t.full_name,
            "email": t.email,
            "phone": t.phone,
            "cin": t.cin,
            "grade": t.grade,
            "speciality": t.speciality,
            "department_name": dept_name,
            "is_active": t.is_active,
        })
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
    elif request.user.role == "teacher":
        attend_qs = attend_qs.filter(session__teacher=request.user)
        session_qs = session_qs.filter(teacher=request.user)
        student_qs = User.objects.filter(
            role="student", student_profile__classe__teachers=request.user
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





def _abs_cache_key(user, params):
    """Generate a deterministic cache key for absence statistics."""
    parts = ["abs-stats", str(user.role), str(user.id)]
    for k in sorted(params.keys()):
        parts.append(f"{k}={params.get(k, '')}")
    from curriculum.views import _cache_key
    return _cache_key(*parts)


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

    # Try cache first
    params = {
        "df": date_from, "dt": date_to,
        "f": filiere_id, "m": module_id,
        "t": teacher_id, "d": department_id,
        "s": semestre_id, "c": classe_id,
    }
    cache_key = _abs_cache_key(request.user, params)
    from curriculum.views import _cached_response
    cached = _cached_response(cache_key, ttl=120)
    if cached:
        return cached

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
    elif request.user.role == "teacher":
        qs = qs.filter(session__teacher=request.user)

    # Combine all aggregate counts into a single query
    agg = qs.aggregate(
        total=Count("id"),
        present=Count("id", filter=Q(attendance_status="confirmed")),
        absent=Count("id", filter=Q(attendance_status="absent")),
        total_students=Count("student_id", distinct=True),
        total_sessions=Count("session_id", distinct=True),
        total_teachers=Count("session__teacher_id", distinct=True),
        total_modules=Count("session__module_id", distinct=True),
        total_filieres=Count("student__classe__filiere_id", distinct=True),
        total_departments=Count("student__classe__department_id", distinct=True),
    )
    total = agg["total"]
    absent = agg["absent"]
    absence_rate = round((absent / total * 100) if total > 0 else 0, 1)

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

    resp_data = {
        "summary": {
            "total": agg["total"],
            "present": agg["present"],
            "absent": agg["absent"],
            "absence_rate": absence_rate,
            "total_students": agg["total_students"],
            "total_sessions": agg["total_sessions"],
            "total_teachers": agg["total_teachers"],
            "total_modules": agg["total_modules"],
            "total_filieres": agg["total_filieres"],
            "total_departments": agg["total_departments"],
        },
        "by_student": by_student,
        "by_teacher": by_teacher,
        "by_module": by_module,
        "by_filiere": by_filiere,
        "by_day": by_day,
        "by_week": by_week,
        "recent_absences": recent_absences,
    }
    from django.core.cache import cache
    cache.set(cache_key, resp_data, 120)
    return Response(resp_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teacher_workload(request):
    """Return teacher workload (total hours) with role-based scoping."""
    from django.db.models import (
        Count, F, ExpressionWrapper, DurationField, FloatField,
        Value, Case, When, Sum,
    )
    from django.db.models.functions import Extract
    from courses.models import Session

    qs = Session.objects.filter(teacher__is_active=True)

    # Role-based scoping
    if request.user.role == "department_head":
        dept = get_user_department(request.user)
        if dept:
            qs = qs.filter(
                Q(classe__department=dept) | Q(classe__filiere__department=dept)
            )
        else:
            qs = qs.none()
    elif request.user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(request.user)
        if filiere_ids:
            qs = qs.filter(classe__filiere_id__in=filiere_ids)
        else:
            qs = qs.none()
    elif request.user.role != "admin":
        return Response({"detail": "Permission refusée."}, status=403)

    # Duration in seconds from (end_time - start_time)
    duration_seconds = Extract(
        ExpressionWrapper(F("end_time") - F("start_time"), output_field=DurationField()),
        "epoch",
    )

    # Adjusted hours based on session type (case-insensitive)
    adjusted_hours = Case(
        When(Q(session_type__istartswith="Cour") | Q(session_type__istartswith="cour"),
             then=duration_seconds / 3600.0),
        When(session_type__iexact="TD", then=duration_seconds / 3600.0 / 1.5),
        When(session_type__iexact="TP", then=duration_seconds / 3600.0 / 1.5),
        default=Value(0.0),
        output_field=FloatField(),
    )

    workload = (
        qs
        .values("teacher_id", "teacher__first_name", "teacher__last_name")
        .annotate(
            session_count=Count("id"),
            total_hours=Sum(adjusted_hours),
        )
        .order_by("-total_hours")
    )

    # Resolve department / filiere for each teacher
    teacher_ids = [w["teacher_id"] for w in workload]
    teacher_info = {}
    if teacher_ids:
        teachers = User.objects.filter(id__in=teacher_ids).prefetch_related(
            Prefetch(
                "assigned_classes",
                queryset=Classe.objects.select_related("department", "filiere"),
            )
        )
        for t in teachers:
            dept_name = None
            filiere_name = None
            ac = list(t.assigned_classes.all())
            if ac:
                c = ac[0]
                if c.department:
                    dept_name = c.department.name
                if c.filiere:
                    filiere_name = c.filiere.name
            teacher_info[t.id] = {"department": dept_name, "filiere": filiere_name}

    result = []
    for w in workload:
        tid = w["teacher_id"]
        info = teacher_info.get(tid, {})
        result.append({
            "id": tid,
            "first_name": w["teacher__first_name"],
            "last_name": w["teacher__last_name"],
            "department": info.get("department"),
            "filiere": info.get("filiere"),
            "session_count": w["session_count"],
            "total_hours": round(w["total_hours"], 2) if w["total_hours"] else 0.0,
        })

    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teacher_workload_dashboard(request):
    """Return teacher workload dashboard data with charts and role-based scoping."""
    from collections import defaultdict
    from courses.models import Session

    qs = Session.objects.filter(teacher__is_active=True)

    # Role-based scoping
    if request.user.role == "department_head":
        dept = get_user_department(request.user)
        if dept:
            qs = qs.filter(
                Q(classe__department=dept) | Q(classe__filiere__department=dept)
            )
        else:
            qs = qs.none()
    elif request.user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(request.user)
        if filiere_ids:
            qs = qs.filter(classe__filiere_id__in=filiere_ids)
        else:
            qs = qs.none()
    elif request.user.role != "admin":
        return Response({"detail": "Permission refusée."}, status=403)

    # Query-param filters
    department_id = request.query_params.get("department_id")
    filiere_id = request.query_params.get("filiere_id")
    semestre_id = request.query_params.get("semestre_id")
    module_id = request.query_params.get("module_id")
    teacher_id = request.query_params.get("teacher_id")
    niveau = request.query_params.get("niveau")
    academic_year = request.query_params.get("academic_year")
    month = request.query_params.get("month")
    year = request.query_params.get("year")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if department_id:
        qs = qs.filter(
            Q(classe__department_id=department_id) |
            Q(classe__filiere__department_id=department_id)
        )
    if filiere_id:
        qs = qs.filter(classe__filiere_id=filiere_id)
    if semestre_id:
        qs = qs.filter(
            Q(classe__semestre_id=semestre_id) |
            Q(classe__filiere__semestre_id=semestre_id)
        )
    if module_id:
        qs = qs.filter(module_id=module_id)
    if teacher_id:
        qs = qs.filter(teacher_id=teacher_id)
    if niveau:
        qs = qs.filter(
            Q(classe__niveau=niveau) | Q(classe__filiere__niveau=niveau)
        )
    if academic_year:
        qs = qs.filter(classe__academic_year=academic_year)
    if month and year:
        qs = qs.filter(date__month=month, date__year=year)
    elif start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    # Prefetch all sessions with related data
    qs = qs.select_related("teacher", "classe", "classe__filiere", "classe__department", "module")

    # Aggregate per teacher + collect distribution data
    rows = defaultdict(lambda: {
        "first_name": "",
        "last_name": "",
        "departments": set(),
        "filieres": set(),
        "cm_hours": 0.0,
        "td_hours": 0.0,
        "tp_hours": 0.0,
        "total_sessions": 0,
    })
    
    dept_totals = defaultdict(lambda: {"cm": 0.0, "td": 0.0, "tp": 0.0, "eq": 0.0})
    filiere_totals = defaultdict(lambda: {"cm": 0.0, "td": 0.0, "tp": 0.0, "eq": 0.0})
    monthly = defaultdict(lambda: {"cm": 0.0, "td": 0.0, "tp": 0.0})

    for s in qs.iterator():
        tid = s.teacher_id
        row = rows[tid]
        if not row["first_name"]:
            row["first_name"] = s.teacher.first_name
            row["last_name"] = s.teacher.last_name

        # Duration in hours
        start_m = s.start_time.hour * 60 + s.start_time.minute
        end_m = s.end_time.hour * 60 + s.end_time.minute
        duration_h = max((end_m - start_m) / 60.0, 0.0)

        st = s.session_type.lower()
        dept_name = None
        filiere_name = None
        if s.classe:
            if s.classe.department:
                dept_name = s.classe.department.name
                row["departments"].add(dept_name)
            if s.classe.filiere:
                filiere_name = s.classe.filiere.name
                row["filieres"].add(filiere_name)

        # Monthly aggregation key
        mk = (s.date.year, s.date.month)

        row["total_sessions"] += 1
        if st.startswith("cour"):
            row["cm_hours"] += duration_h
            monthly[mk]["cm"] += duration_h
            if dept_name: dept_totals[dept_name]["cm"] += duration_h
            if filiere_name: filiere_totals[filiere_name]["cm"] += duration_h
        elif st == "td":
            row["td_hours"] += duration_h
            monthly[mk]["td"] += duration_h
            if dept_name: dept_totals[dept_name]["td"] += duration_h
            if filiere_name: filiere_totals[filiere_name]["td"] += duration_h
        elif st == "tp":
            row["tp_hours"] += duration_h
            monthly[mk]["tp"] += duration_h
            if dept_name: dept_totals[dept_name]["tp"] += duration_h
            if filiere_name: filiere_totals[filiere_name]["tp"] += duration_h

    # Compute equivalent hours and build result
    result = []
    for tid, row in rows.items():
        cm = row["cm_hours"]
        td = row["td_hours"]
        tp = row["tp_hours"]
        equivalent = cm + (td / 1.5) + (tp / 1.5)
        result.append({
            "id": tid,
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "department": ", ".join(sorted(row["departments"])) if row["departments"] else None,
            "filieres": ", ".join(sorted(row["filieres"])) if row["filieres"] else None,
            "cm_hours": round(cm, 2),
            "td_hours": round(td, 2),
            "tp_hours": round(tp, 2),
            "total_sessions": row["total_sessions"],
            "equivalent_hours": round(equivalent, 2),
        })

    # Sort by equivalent_hours descending
    result.sort(key=lambda x: x["equivalent_hours"], reverse=True)

    # Compute equivalent for dept/filiere totals
    for d in dept_totals.values():
        d["eq"] = d["cm"] + (d["td"] / 1.5) + (d["tp"] / 1.5)
    for f in filiere_totals.values():
        f["eq"] = f["cm"] + (f["td"] / 1.5) + (f["tp"] / 1.5)

    # Sort distribution data by eq descending
    dept_sorted = sorted(dept_totals.items(), key=lambda x: x[1]["eq"], reverse=True)
    filiere_sorted = sorted(filiere_totals.items(), key=lambda x: x[1]["eq"], reverse=True)

    total_eq = sum(r["equivalent_hours"] for r in result)
    top_teacher = result[0] if result else None
    totals = {
        "cm_hours": round(sum(r["cm_hours"] for r in result), 2),
        "td_hours": round(sum(r["td_hours"] for r in result), 2),
        "tp_hours": round(sum(r["tp_hours"] for r in result), 2),
        "total_sessions": sum(r["total_sessions"] for r in result),
        "equivalent_hours": round(total_eq, 2),
        "teacher_count": len(result),
        "average_equivalent": round(total_eq / len(result), 2) if result else 0,
        "top_teacher": {
            "name": f"{top_teacher['first_name']} {top_teacher['last_name']}",
            "equivalent_hours": top_teacher["equivalent_hours"],
        } if top_teacher else None,
    }

    # Chart data — ALL teachers for the main bar chart
    chart_data = {
        "labels": [f"{r['first_name']} {r['last_name']}" for r in result],
        "equivalent_hours": [r["equivalent_hours"] for r in result],
        "cm_hours": [r["cm_hours"] for r in result],
        "td_hours": [r["td_hours"] for r in result],
        "tp_hours": [r["tp_hours"] for r in result],
    }

    # Department distribution chart
    chart_data["dept_labels"] = [d[0] for d in dept_sorted]
    chart_data["dept_eq"] = [round(d[1]["eq"], 2) for d in dept_sorted]

    # Filiere distribution chart
    chart_data["filiere_labels"] = [f[0] for f in filiere_sorted]
    chart_data["filiere_eq"] = [round(f[1]["eq"], 2) for f in filiere_sorted]

    # Monthly trend
    month_keys = sorted(monthly.keys())
    chart_data["monthly_labels"] = [f"{m[1]:02d}/{m[0]}" for m in month_keys]
    chart_data["monthly_cm"] = [round(monthly[m]["cm"], 2) for m in month_keys]
    chart_data["monthly_td"] = [round(monthly[m]["td"], 2) for m in month_keys]
    chart_data["monthly_tp"] = [round(monthly[m]["tp"], 2) for m in month_keys]

    return Response({
        "teachers": result,
        "totals": totals,
        "chart_data": chart_data,
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

    from django.db.models import Count, Q
    from curriculum.views import _cache_key, _cached_response

    cache_key = _cache_key("dash-counts", str(user.role), str(user.id))
    cached = _cached_response(cache_key, ttl=60)
    if cached:
        return cached

    if user.role == "admin":
        user_agg = User.objects.aggregate(
            users=Count("id"),
            admins=Count("id", filter=Q(role="admin")),
            teachers=Count("id", filter=Q(role="teacher")),
            assistants=Count("id", filter=Q(is_also_teacher=True)),
            students=Count("id", filter=Q(role="student")),
            department_heads=Count("id", filter=Q(role="department_head")),
            program_managers=Count("id", filter=Q(role="program_manager")),
        )
        session_agg = Session.objects.aggregate(
            sessions=Count("id"),
            active_sessions=Count("id", filter=Q(is_active=True)),
            closed_sessions=Count("id", filter=Q(is_closed=True)),
            reports=Count("id", filter=~Q(report_file="")),
        )
        attendance_agg = Attendance.objects.aggregate(
            attendances=Count("id"),
            present=Count("id", filter=Q(attendance_status="confirmed")),
            absent=Count("id", filter=Q(attendance_status="absent")),
        )
        return Response({
            **user_agg,
            "classes": Classe.objects.count(),
            "filieres": Filiere.objects.count(),
            "modules": Module.objects.count(),
            "departments": Department.objects.count(),
            "blocks": Block.objects.count(),
            "rooms": Room.objects.count(),
            "amphitheaters": Amphitheater.objects.count(),
            **session_agg,
            **attendance_agg,
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
                | Q(role="teacher", assigned_classes__department=dept)
                | Q(role="teacher", assigned_classes__filiere__department=dept)
                | Q(role="teacher", sessions__classe__department=dept)
                | Q(role="teacher", sessions__classe__filiere__department=dept)
                | Q(role="teacher", taught_modules__filiere__department=dept)
                | Q(role__in=("department_head", "program_manager"), headed_department=dept)
                | Q(role="student", student_profile__classe__department=dept)
                | Q(role="student", student_profile__classe__filiere__department=dept)
                | Q(role="teacher", assigned_classes__department=dept, is_also_teacher=True)
                | Q(role="teacher", assigned_classes__filiere__department=dept, is_also_teacher=True)
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

    user_agg = users_qs.aggregate(
        users=Count("id"),
        admins=Count("id", filter=Q(role="admin")),
        teachers=Count("id", filter=Q(role="teacher")),
        assistants=Count("id", filter=Q(is_also_teacher=True)),
        students=Count("id", filter=Q(role="student")),
        department_heads=Count("id", filter=Q(role="department_head")),
        program_managers=Count("id", filter=Q(role="program_manager")),
    )
    session_agg = sessions_qs.aggregate(
        sessions=Count("id"),
        active_sessions=Count("id", filter=Q(is_active=True)),
        closed_sessions=Count("id", filter=Q(is_closed=True)),
        reports=Count("id", filter=~Q(report_file="")),
    )
    attendance_agg = attendances_qs.aggregate(
        attendances=Count("id"),
        present=Count("id", filter=Q(attendance_status="confirmed")),
        absent=Count("id", filter=Q(attendance_status="absent")),
    )
    resp_data = {
        **user_agg,
        "classes": classes_qs.count(),
        "filieres": filieres_qs.count(),
        "modules": modules_qs.count(),
        "departments": dept_count,
        "blocks": Block.objects.count(),
        "rooms": Room.objects.count(),
        "amphitheaters": Amphitheater.objects.count(),
        **session_agg,
        **attendance_agg,
    }
    from django.core.cache import cache
    cache.set(cache_key, resp_data, 60)
    return Response(resp_data)


# ═══════════════════════════════════════════════════════════════
# Password Reset
# ═══════════════════════════════════════════════════════════════

class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        role = request.data.get("role", "student").strip().lower()
        first_name = request.data.get("first_name", "").strip().lower()
        last_name = request.data.get("last_name", "").strip().lower()
        email = request.data.get("email", "").strip().lower()

        missing = []
        if not first_name:
            missing.append("Prénom")
        if not last_name:
            missing.append("Nom")
        if not email:
            missing.append("Email")

        if role == "teacher":
            identifier = request.data.get("cin", "").strip()
            ident_label = "CNE / CIN"
        else:
            identifier = request.data.get("code_massar", "").strip()
            ident_label = "Code Massar"

        if not identifier:
            missing.append(ident_label)

        if missing:
            return Response(
                {"detail": f"Champs obligatoires : {', '.join(missing)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email, is_active=True).first()
        msg = "Identifiants incorrects. Veuillez vérifier vos informations."

        if user:
            if role == "teacher":
                if user.role != "teacher":
                    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
                if (
                    user.first_name.strip().lower() != first_name
                    or user.last_name.strip().lower() != last_name
                    or (user.cin or "").strip().lower() != identifier.lower()
                ):
                    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
            else:
                from users.models import Student
                student = Student.objects.filter(
                    user=user,
                    first_name__iexact=first_name,
                    last_name__iexact=last_name,
                    code_massar__iexact=identifier,
                ).first()
                if not student:
                    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

            token_generator = PasswordResetTokenGenerator()
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            reset_url = f"{request.scheme}://{request.get_host()}/password-reset/{uidb64}/{token}/"

            logger.info(f"Password reset link for {email} (role={role}): {reset_url}")

            from django.conf import settings
            try:
                from django.core.mail import send_mail
                subject = "Reinitialisation de votre mot de passe - PresenceQR"
                message = (
                    f"Bonjour {user.first_name},\n\n"
                    f"Vous avez demande la reinitialisation de votre mot de passe.\n\n"
                    f"Cliquez sur le lien ci-dessous pour definir un nouveau mot de passe :\n"
                    f"{reset_url}\n\n"
                    f"Ce lien est valable 24 heures.\n\n"
                    f"---\nPresenceQR"
                )
                send_mail(
                    subject, message,
                    settings.DEFAULT_FROM_EMAIL or "noreply@presenceqr.ma",
                    [email], fail_silently=True,
                )
            except Exception as e:
                logger.warning(f"Email sending failed for {email}: {e}")

            return Response({
                "detail": "Identifiants vérifiés. Utilisez le lien ci-dessous.",
                "reset_url": reset_url,
            })

        return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uidb64 = request.data.get("uidb64", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        if not uidb64 or not token or not new_password:
            return Response(
                {"detail": "Champs requis manquants."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {"detail": "Le mot de passe doit contenir au moins 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Lien de reinitialisation invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            return Response(
                {"detail": "Lien de reinitialisation invalide ou expire."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        logger.info(f"Password reset successful for {user.email}")

        return Response({"detail": "Mot de passe reinitialise avec succes."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teacher_monthly_report(request):
    """Generate an Excel report of teacher monthly workload with role-based scoping."""
    from collections import defaultdict
    from datetime import date as date_module
    from courses.models import Session
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter

    qs = Session.objects.filter(teacher__is_active=True)

    # Role-based scoping
    if request.user.role == "department_head":
        dept = get_user_department(request.user)
        if dept:
            qs = qs.filter(
                Q(classe__department=dept) | Q(classe__filiere__department=dept)
            )
        else:
            qs = qs.none()
    elif request.user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(request.user)
        if filiere_ids:
            qs = qs.filter(classe__filiere_id__in=filiere_ids)
        else:
            qs = qs.none()
    elif request.user.role != "admin":
        return Response({"detail": "Permission refusée."}, status=403)

    # Query-param filters
    department_id = request.query_params.get("department_id")
    niveau = request.query_params.get("niveau")
    semestre_id = request.query_params.get("semestre_id")
    filiere_id = request.query_params.get("filiere_id")
    module_id = request.query_params.get("module_id")
    teacher_id = request.query_params.get("teacher_id")
    month = request.query_params.get("month")
    year = request.query_params.get("year")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if department_id:
        qs = qs.filter(
            Q(classe__department_id=department_id) |
            Q(classe__filiere__department_id=department_id)
        )
    if niveau:
        qs = qs.filter(
            Q(classe__niveau=niveau) | Q(classe__filiere__niveau=niveau)
        )
    if semestre_id:
        qs = qs.filter(
            Q(classe__semestre_id=semestre_id) | Q(classe__filiere__semestre_id=semestre_id)
        )
    if filiere_id:
        qs = qs.filter(classe__filiere_id=filiere_id)
    if module_id:
        qs = qs.filter(module_id=module_id)
    if teacher_id:
        qs = qs.filter(teacher_id=teacher_id)
    if month and year:
        qs = qs.filter(date__month=month, date__year=year)
    elif start_date:
        qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

    # Optimised prefetch of all relations needed for columns
    qs = qs.select_related(
        "teacher",
        "module",
        "classe",
        "classe__department",
        "classe__filiere",
        "classe__filiere__semestre",
    ).order_by("teacher__last_name", "teacher__first_name", "module__name")

    # KEY: (teacher_id, module_id) — one row per teacher+module
    key_order: list[tuple[int, int | None]] = []
    rows: dict[tuple[int, int | None], dict] = defaultdict(lambda: {
        "teacher_name": "",
        "department": set(),
        "niveau": set(),
        "semestre": set(),
        "filiere": set(),
        "module_name": None,
        "cm_count": 0, "td_count": 0, "tp_count": 0,
        "cm_hours": 0.0, "td_hours": 0.0, "tp_hours": 0.0,
        "total_hours": 0.0, "total_sessions": 0,
    })

    for s in qs.iterator():
        tid = s.teacher_id
        mid = s.module_id
        key = (tid, mid)

        if key not in rows:
            key_order.append(key)
            rows[key]["teacher_name"] = f"{s.teacher.last_name} {s.teacher.first_name}"
            rows[key]["module_name"] = s.module.name if s.module else "—"

        # Duration in hours via simple minute arithmetic
        start_m = s.start_time.hour * 60 + s.start_time.minute
        end_m = s.end_time.hour * 60 + s.end_time.minute
        duration_h = max((end_m - start_m) / 60.0, 0.0)

        # Metadata from classe
        if s.classe:
            if s.classe.department:
                rows[key]["department"].add(s.classe.department.name)
            if s.classe.niveau:
                rows[key]["niveau"].add(s.classe.niveau)
            if s.classe.filiere:
                rows[key]["filiere"].add(s.classe.filiere.name)
                if s.classe.filiere.semestre:
                    rows[key]["semestre"].add(s.classe.filiere.semestre.name)

        row = rows[key]
        row["total_sessions"] += 1
        st = s.session_type.lower()
        if st.startswith("cour"):
            row["cm_count"] += 1
            row["cm_hours"] += duration_h
            row["total_hours"] += duration_h
        elif st == "td":
            row["td_count"] += 1
            adjusted = duration_h / 1.5
            row["td_hours"] += adjusted
            row["total_hours"] += adjusted
        elif st == "tp":
            row["tp_count"] += 1
            adjusted = duration_h / 1.5
            row["tp_hours"] += adjusted
            row["total_hours"] += adjusted

    def _fmt_set(s: set) -> str:
        return ", ".join(sorted(s)) if s else "—"

    # ── Generate Excel ──
    wb = Workbook()
    ws = wb.active
    ws.title = "Charge Horaire"

    bold = Font(bold=True)
    header_align = Alignment(horizontal="center", vertical="center")

    headers = [
        "Enseignant",
        "Département", "Niveau", "Semestre", "Filière", "Module",
        "Nb séances CM", "Nb séances TD", "Nb séances TP",
        "Total heures CM", "Total heures TD", "Total heures TP",
        "Charge horaire totale", "Nombre total de séances",
    ]

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = bold
        cell.alignment = header_align

    totals = {
        "cm_count": 0, "td_count": 0, "tp_count": 0,
        "cm_hours": 0.0, "td_hours": 0.0, "tp_hours": 0.0,
        "total_hours": 0.0, "total_sessions": 0,
    }

    for row_idx, key in enumerate(key_order, 2):
        r = rows[key]
        ws.cell(row=row_idx, column=1, value=r["teacher_name"])
        ws.cell(row=row_idx, column=2, value=_fmt_set(r["department"]))
        ws.cell(row=row_idx, column=3, value=_fmt_set(r["niveau"]))
        ws.cell(row=row_idx, column=4, value=_fmt_set(r["semestre"]))
        ws.cell(row=row_idx, column=5, value=_fmt_set(r["filiere"]))
        ws.cell(row=row_idx, column=6, value=r["module_name"] or "—")
        ws.cell(row=row_idx, column=7, value=r["cm_count"])
        ws.cell(row=row_idx, column=8, value=r["td_count"])
        ws.cell(row=row_idx, column=9, value=r["tp_count"])
        ws.cell(row=row_idx, column=10, value=round(r["cm_hours"], 2))
        ws.cell(row=row_idx, column=11, value=round(r["td_hours"], 2))
        ws.cell(row=row_idx, column=12, value=round(r["tp_hours"], 2))
        ws.cell(row=row_idx, column=13, value=round(r["total_hours"], 2))
        ws.cell(row=row_idx, column=14, value=r["total_sessions"])

        totals["cm_count"] += r["cm_count"]
        totals["td_count"] += r["td_count"]
        totals["tp_count"] += r["tp_count"]
        totals["cm_hours"] += r["cm_hours"]
        totals["td_hours"] += r["td_hours"]
        totals["tp_hours"] += r["tp_hours"]
        totals["total_hours"] += r["total_hours"]
        totals["total_sessions"] += r["total_sessions"]

    # Total row
    total_row = len(key_order) + 2
    total_cells = [
        (1, "TOTAL GÉNÉRAL"),
        (7, totals["cm_count"]), (8, totals["td_count"]), (9, totals["tp_count"]),
        (10, round(totals["cm_hours"], 2)),
        (11, round(totals["td_hours"], 2)),
        (12, round(totals["tp_hours"], 2)),
        (13, round(totals["total_hours"], 2)),
        (14, totals["total_sessions"]),
    ]
    for col, val in total_cells:
        c = ws.cell(row=total_row, column=col, value=val)
        c.font = bold

    # Auto-adjust column widths
    for col_idx in range(1, len(headers) + 1):
        max_len = len(str(headers[col_idx - 1]))
        for r_idx in range(2, total_row + 1):
            val = ws.cell(row=r_idx, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 4

    if month and year:
        fn = f"Charge_Horaire_Enseignants_{month}_{year}.xlsx"
    else:
        fn = f"Charge_Horaire_Enseignants_{date_module.today().strftime('%m_%Y')}.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{fn}"'
    wb.save(response)
    return response


# ────────────────────────────────────────────────────────────
# Landing Page Statistics
# ────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def landing_stats(request):
    """Public endpoint returning real counts for the landing page counters."""
    from django.db.models import Count, Q, Sum, F, ExpressionWrapper, fields
    from attendance.models import Attendance
    from courses.models import Session
    from curriculum.models import Filiere, Module
    from users.models import Classe, Department

    def _safe_count(qs):
        try:
            return qs.count()
        except Exception:
            return 0

    user_agg = User.objects.aggregate(
        students=Count("id", filter=Q(role="student")),
        teachers=Count("id", filter=Q(role="teacher")),
    )
    classes_count = _safe_count(Classe.objects.all())
    modules_count = _safe_count(Module.objects.all())
    sessions_count = _safe_count(Session.objects.all())
    departments_count = _safe_count(Department.objects.all())
    filieres_count = _safe_count(Filiere.objects.all())

    attendance_agg = {"attendances": 0, "present": 0, "absent": 0}
    try:
        attendance_agg = Attendance.objects.aggregate(
            attendances=Count("id"),
            present=Count("id", filter=Q(attendance_status="confirmed")),
            absent=Count("id", filter=Q(attendance_status="absent")),
        )
    except Exception:
        pass

    total_attendance = attendance_agg["attendances"]
    total_present = attendance_agg["present"]
    attendance_rate = round((total_present / total_attendance * 100) if total_attendance > 0 else 0, 1)

    total_hours = 0
    try:
        from django.db import connection
        if connection.vendor == "postgresql":
            result = Session.objects.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("end_time") - F("start_time"),
                        output_field=fields.DurationField(),
                    )
                )
            )
            if result["total"] is not None:
                total_hours = round(result["total"].total_seconds() / 3600, 1)
        else:
            for s in Session.objects.iterator():
                from datetime import datetime
                start = datetime.combine(s.date, s.start_time)
                end = datetime.combine(s.date, s.end_time)
                total_hours += (end - start).total_seconds() / 3600
            total_hours = round(total_hours, 1)
    except Exception:
        total_hours = 0

    return Response({
        **user_agg,
        "classes": classes_count,
        "modules": modules_count,
        "sessions": sessions_count,
        "departments": departments_count,
        "filieres": filieres_count,
        **attendance_agg,
        "attendance_rate": attendance_rate,
        "total_hours": total_hours,
    })