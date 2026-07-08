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

from .models import Amphitheater, Block, Classe, Room, Student, User
from .permissions import IsAdmin, IsAdminOrTeacher
from .serializers import (
    ClasseSerializer,
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
        if self.request.user.role == "teacher":
            qs = qs.filter(
                Q(classe__teachers=self.request.user)
                | Q(classe__sessions__teacher=self.request.user)
            ).distinct()
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


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def teacher_list(request):
    teachers = User.objects.filter(role="teacher", is_active=True).order_by("last_name", "first_name")
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
