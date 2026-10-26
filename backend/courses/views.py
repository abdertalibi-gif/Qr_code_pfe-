import base64
import logging
import threading
from contextlib import nullcontext
from io import BytesIO

import qrcode
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.site_url import build_attend_url
from users.models import Amphitheater, Block, Room, User
from users.permissions import (
    IsAdminOrTeacher,
    apply_role_filtering,
    get_user_department,
    get_user_filiere_ids,
)

from .models import Session
from .serializers import GenerateQRSerializer, SessionSerializer
from .utils import (
    TEACHER_SESSION_OVERLAP_MESSAGE,
    get_occupied_location_ids,
    get_teacher_conflicting_sessions,
)

logger = logging.getLogger(__name__)

# Verrous applicatifs par enseignant. Ils sérialisent la vérification de
# chevauchement et l'écriture au sein d'un même processus. En production
# multi-processus, `select_for_update()` sur la ligne enseignant assure la
# sérialisation au niveau base de données (PostgreSQL).
_teacher_locks_guard = threading.Lock()
_teacher_locks = {}


def _get_teacher_lock(teacher_id):
    key = str(teacher_id)
    with _teacher_locks_guard:
        lock = _teacher_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _teacher_locks[key] = lock
        return lock


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get_queryset(self):
        user = self.request.user
        qs = Session.objects.select_related(
            "teacher",
            "classe",
            "classe__filiere",
            "classe__semestre",
            "module",
            "semestre",
            "filiere",
            "block",
            "room",
            "amphitheater",
        ).order_by("-date", "-start_time", "-id")

        if user.role == "teacher":
            qs = qs.filter(teacher=user)
        elif user.role == "department_head":
            qs = apply_role_filtering(qs, "session", self.request)
        elif user.role == "program_manager":
            qs = apply_role_filtering(qs, "session", self.request)

        classe_id = self.request.query_params.get("classe")
        if classe_id:
            qs = qs.filter(classe_id=classe_id)
        teacher_id = self.request.query_params.get("teacher")
        if teacher_id:
            qs = qs.filter(teacher_id=teacher_id)
        return qs

    def get_permissions(self):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role in ("department_head", "program_manager"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def _ensure_no_teacher_overlap(self, serializer, exclude_session_id=None):
        """Re-vérifie le chevauchement enseignant sous verrou base de données.

        Appelé dans ``transaction.atomic()`` depuis ``perform_create`` et
        ``perform_update`` afin qu'une requête concurrente ne puisse pas se
        glisser entre la validation du serializer et l'écriture.
        """
        validated = serializer.validated_data
        instance = serializer.instance

        teacher = validated.get("teacher")
        if teacher is None and instance is not None:
            teacher = instance.teacher
        if teacher is None and getattr(self.request.user, "role", None) == "teacher":
            teacher = self.request.user
        if teacher is None:
            return

        date = validated.get("date", getattr(instance, "date", None))
        start_time = validated.get(
            "start_time", getattr(instance, "start_time", None)
        )
        end_time = validated.get("end_time", getattr(instance, "end_time", None))
        if not (date and start_time and end_time):
            return

        # Verrou pessimiste sur la ligne enseignant (efficace sous PostgreSQL).
        User.objects.select_for_update().get(pk=teacher.pk)

        conflicts = get_teacher_conflicting_sessions(
            teacher_id=teacher.pk,
            date=date,
            start_time=start_time,
            end_time=end_time,
            exclude_session_id=exclude_session_id,
        )
        if conflicts.exists():
            raise serializers.ValidationError(TEACHER_SESSION_OVERLAP_MESSAGE)

    def perform_create(self, serializer):
        try:
            user = self.request.user
            if user.role == "department_head":
                dept = get_user_department(user)
                classe = serializer.validated_data.get("classe")
                if classe and dept:
                    if classe.department_id != dept.id and classe.filiere.department_id != dept.id:
                        raise serializers.ValidationError({"classe": "Cette classe ne fait pas partie de votre département."})
            if user.role == "program_manager":
                filiere_ids = get_user_filiere_ids(user)
                classe = serializer.validated_data.get("classe")
                if classe and filiere_ids and classe.filiere_id not in filiere_ids:
                    raise serializers.ValidationError({"classe": "Cette classe ne fait pas partie de vos filières."})
            with transaction.atomic():
                self._ensure_no_teacher_overlap(serializer)
                if user.role == "teacher":
                    session = serializer.save(teacher=user)
                else:
                    if "teacher" not in serializer.validated_data or not serializer.validated_data.get("teacher"):
                        raise serializers.ValidationError({"teacher": "Un enseignant doit être sélectionné."})
                    session = serializer.save()
                teacher = session.teacher
                if teacher.role == "teacher":
                    teacher.assigned_classes.add(session.classe)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError({"detail": f"Erreur lors de la création de la séance: {str(e)}"})

    def perform_update(self, serializer):
        try:
            instance = serializer.instance
            with transaction.atomic():
                self._ensure_no_teacher_overlap(
                    serializer, exclude_session_id=instance.pk
                )
                session = serializer.save()
                teacher = session.teacher
                if teacher.role == "teacher":
                    teacher.assigned_classes.add(session.classe)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError({"detail": f"Erreur lors de la modification de la séance: {str(e)}"})

    def create(self, request, *args, **kwargs):
        # Verrou applicatif par enseignant : couvre les validations et
        # l'écriture, y compris sous SQLite (mono-processus). Le verrou base
        # de données de perform_create reste actif pour le multi-processus.
        teacher_id = None
        if getattr(request.user, "role", None) == "teacher":
            teacher_id = request.user.pk
        elif hasattr(request.data, "get"):
            teacher_id = request.data.get("teacher")
        lock = _get_teacher_lock(teacher_id) if teacher_id else nullcontext()
        with lock:
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        teacher_id = None
        if hasattr(request.data, "get"):
            teacher_id = request.data.get("teacher")
        if not teacher_id:
            teacher_id = instance.teacher_id
        lock = _get_teacher_lock(teacher_id) if teacher_id else nullcontext()
        with lock:
            return super().update(request, *args, **kwargs)

    def _check_session_access(self, request, session):
        if not session.teacher_can_manage(request.user):
            return False
        return True

    def _build_qr_payload(self, request, session):
        qr_url = build_attend_url(request, session.qr_token)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode("utf-8")

        return {
            "qr_token": session.qr_token,
            "qr_session_id": session.qr_session_id,
            "qr_expires_at": session.qr_expires_at,
            "qr_url": qr_url,
            "attendance_radius_meters": session.attendance_radius_meters,
            "location_latitude": session.location_latitude,
            "location_longitude": session.location_longitude,
            "is_qr_valid": session.is_qr_valid,
            "qr_image_base64": f"data:image/png;base64,{b64}",
        }

    @action(detail=False, methods=["get"], url_path="available-rooms")
    def available_rooms(self, request):
        """Return rooms/amphitheaters available for a given date/time slot."""
        date = request.query_params.get("date")
        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")
        location_type = request.query_params.get("location_type")
        exclude_id = request.query_params.get("exclude_session_id")

        if not all([date, start_time, end_time]):
            return Response(
                {"error": "Les paramètres date, start_time et end_time sont requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        occupied = get_occupied_location_ids(
            date, start_time, end_time, exclude_session_id=exclude_id
        )

        if location_type == "block" or not location_type:
            blocks_data = []
            from users.models import Block
            blocks = Block.objects.prefetch_related("rooms").order_by("name")
            for b in blocks:
                available_rooms = [
                    {"id": r.id, "name": r.name}
                    for r in b.rooms.all()
                    if r.id not in occupied["room_ids"]
                ]
                blocks_data.append({
                    "id": b.id,
                    "name": b.name,
                    "rooms": available_rooms,
                })
            if location_type == "block":
                return Response({"blocks": blocks_data})
            elif not location_type:
                from users.models import Amphitheater
                amphis = Amphitheater.objects.all().order_by("name").values("id", "name")
                available_amphis = [
                    a for a in amphis
                    if a["id"] not in occupied["amphitheater_ids"]
                ]
                return Response({"blocks": blocks_data, "amphitheaters": list(available_amphis)})

        if location_type == "amphitheater":
            from users.models import Amphitheater
            amphis = Amphitheater.objects.all().order_by("name").values("id", "name")
            available = [
                a for a in amphis
                if a["id"] not in occupied["amphitheater_ids"]
            ]
            return Response({"amphitheaters": list(available)})

        return Response({"error": "Type de lieu invalide."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="available-locations")
    def available_locations(self, request):
        """Return all available rooms, blocks, and amphitheaters for a date/time slot."""
        date = request.query_params.get("date")
        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")
        exclude_id = request.query_params.get("exclude_session_id")

        if not all([date, start_time, end_time]):
            return Response(
                {"error": "Les paramètres date, start_time et end_time sont requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        occupied = get_occupied_location_ids(
            date, start_time, end_time, exclude_session_id=exclude_id
        )

        from django.db.models import F
        available_rooms = (
            Room.objects.filter(block__isnull=False)
            .exclude(id__in=occupied["room_ids"])
            .annotate(block_name=F("block__name"))
            .order_by("block__name", "name")
            .values("id", "name", "block_id", "block_name")
        )

        blocks_data = []
        for b in Block.objects.prefetch_related("rooms").order_by("name"):
            rooms = [
                {"id": r.id, "name": r.name}
                for r in b.rooms.all()
                if r.id not in occupied["room_ids"]
            ]
            blocks_data.append({
                "id": b.id,
                "name": b.name,
                "rooms": rooms,
            })

        available_amphis = (
            Amphitheater.objects.all()
            .exclude(id__in=occupied["amphitheater_ids"])
            .order_by("name")
            .values("id", "name")
        )

        return Response({
            "rooms": list(available_rooms),
            "blocks": blocks_data,
            "amphitheaters": list(available_amphis),
        })

    @action(detail=True, methods=["get"], url_path="current-qr")
    def current_qr(self, request, pk=None):
        session = self.get_object()

        if not self._check_session_access(request, session):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if not session.qr_token:
            return Response(
                {"error": "Aucun QR généré pour cette séance."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            self._build_qr_payload(request, session),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="generate-qr")
    def generate_qr(self, request, pk=None):
        session = self.get_object()

        if not self._check_session_access(request, session):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role == "teacher":
            if session.teacher_id != request.user.id:
                if not session.classe.teachers.filter(pk=request.user.pk).exists():
                    return Response(
                        {"error": "Vous ne pouvez générer un QR que pour vos classes."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        if not session.can_generate_qr:
            current = timezone.now()
            start, end = session._session_window_bounds()
            if current < start:
                msg = (
                    f"La séance commence à {session.start_time.strftime('%H:%M')}. "
                    "Le QR sera disponible pendant le créneau horaire."
                )
            else:
                msg = (
                    f"Le créneau horaire est terminé "
                    f"({session.start_time.strftime('%H:%M')}–"
                    f"{session.end_time.strftime('%H:%M')}). "
                    "Consultez les statistiques ou exportez les présences."
                )
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

        ser = GenerateQRSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        expiry = ser.validated_data["expiry_minutes"]
        radius = ser.validated_data["attendance_radius_meters"]
        latitude = ser.validated_data.get("latitude")
        longitude = ser.validated_data.get("longitude")

        session.generate_qr_token(
            expiry_minutes=expiry,
            attendance_radius_meters=radius,
            latitude=latitude,
            longitude=longitude,
        )

        logger.info(
            f"QR generated for session {session.id} by {request.user.email}, "
            f"expires at {session.qr_expires_at}"
        )

        return Response(
            self._build_qr_payload(request, session),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        session = self.get_object()

        if not self._check_session_access(request, session):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if session.is_closed:
            return Response(
                {
                    "status": "already_closed",
                    "report_url": session.report_file.url if session.report_file else None,
                },
                status=status.HTTP_200_OK,
            )

        try:
            filename = session.close_session()
            logger.info(f"Session {session.id} closed manually by {request.user.email}. Report generated: {filename}")
            return Response(
                {
                    "status": "closed",
                    "report_url": session.report_file.url if session.report_file else None,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error closing session {session.id}: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Erreur lors de la clôture de la séance: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
