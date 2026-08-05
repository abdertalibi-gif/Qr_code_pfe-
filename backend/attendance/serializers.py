from rest_framework import serializers

from courses.models import Session

from .models import Attendance, SuspiciousAttempt
from .utils import round_coordinate

class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_code_massar = serializers.CharField(
        source="student.code_massar", read_only=True
    )
    student_first_name = serializers.CharField(
        source="student.first_name", read_only=True
    )
    student_last_name = serializers.CharField(
        source="student.last_name", read_only=True
    )
    classe_name = serializers.SerializerMethodField()
    session_date = serializers.DateField(source="session.date", read_only=True)
    subject = serializers.CharField(source="session.subject", read_only=True)
    classe_session = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    professor_id = serializers.IntegerField(source="session.teacher_id", read_only=True)
    course_id = serializers.IntegerField(source="session.id", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "student",
            "student_name",
            "student_first_name",
            "student_last_name",
            "student_code_massar",
            "classe_name",
            "session",
            "course_id",
            "professor_id",
            "session_date",
            "subject",
            "classe_session",
            "teacher_name",
            "validation_time",
            "ip_address",
            "device_id",
            "device_fingerprint",
            "device_info",
            "latitude",
            "longitude",
            "qr_session_id",
            "attendance_status",
        ]
        read_only_fields = ["id", "validation_time", "ip_address"]

    def get_classe_name(self, obj):
        return str(obj.student.classe)

    def get_classe_session(self, obj):
        return str(obj.session.classe)

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_teacher_name(self, obj):
        teacher = obj.session.teacher
        return teacher.full_name


class SuspiciousAttemptSerializer(serializers.ModelSerializer):
    session_subject = serializers.CharField(
        source="session.subject", read_only=True, default=""
    )
    session_date = serializers.DateField(
        source="session.date", read_only=True, default=None
    )

    class Meta:
        model = SuspiciousAttempt
        fields = [
            "id",
            "session",
            "session_subject",
            "session_date",
            "attempt_type",
            "qr_token",
            "qr_session_id",
            "code_massar",
            "first_name",
            "last_name",
            "ip_address",
            "device_id",
            "device_fingerprint",
            "device_info",
            "latitude",
            "longitude",
            "error_message",
            "created_at",
        ]


class ValidateAttendanceSerializer(serializers.Serializer):
    qr_token = serializers.CharField(max_length=100)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    code_massar = serializers.CharField(max_length=50)
    device_id = serializers.CharField(max_length=255, required=False, default="")
    device_fingerprint = serializers.CharField(
        max_length=64, required=False, default=""
    )
    device_info = serializers.CharField(required=False, default="")
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, required=False, allow_null=True
    )

    def validate_latitude(self, value):
        return round_coordinate(value)

    def validate_longitude(self, value):
        return round_coordinate(value)


class ValidateAppAttendanceSerializer(serializers.Serializer):
    qr_token = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=255, required=False, default="")
    device_fingerprint = serializers.CharField(
        max_length=64, required=False, default=""
    )
    device_info = serializers.CharField(required=False, default="")
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, required=False, allow_null=True
    )

    def validate_latitude(self, value):
        return round_coordinate(value)

    def validate_longitude(self, value):
        return round_coordinate(value)


class StudentScheduleSerializer(serializers.ModelSerializer):
    """Séances de l'emploi du temps d'un étudiant (lecture seule).

    N'expose jamais qr_token / qr_session_id — l'étudiant ne doit pas pouvoir
    valider lui-même sa présence avec le QR de l'enseignant.
    """

    module_name = serializers.CharField(source="module.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    block_name = serializers.CharField(source="block.name", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)
    amphitheater_name = serializers.CharField(source="amphitheater.name", read_only=True)
    classe_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    qr_open = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            "id",
            "subject",
            "module_name",
            "teacher_name",
            "classe",
            "classe_name",
            "location_type",
            "block_name",
            "room_name",
            "amphitheater_name",
            "date",
            "start_time",
            "end_time",
            "session_type",
            "is_active",
            "is_closed",
            "qr_expires_at",
            "is_within_session_window",
            "status",
            "qr_open",
        ]

    def get_classe_name(self, obj):
        return str(obj.classe)

    def get_status(self, obj):
        from django.utils import timezone

        if not obj.is_active:
            return "annulee"
        now = timezone.now()
        start, end = obj._session_window_bounds()
        if now < start:
            return "a_venir"
        if start <= now <= end:
            return "en_cours"
        return "terminee"

    def get_qr_open(self, obj):
        return bool(obj.is_qr_valid)
