from django.db.models import Q
from rest_framework import serializers

from attendance.utils import round_coordinate
from curriculum.models import Module
from users.models import Classe, User, Block, Room, Amphitheater

from .models import Session


class SessionSerializer(serializers.ModelSerializer):
    session_type = serializers.ChoiceField(
        choices=[("Cours", "Cours"), ("TD", "TD"), ("TP", "TP"), ("Exam", "Exam"), ("Other", "Autre")],
        default="Cours",
    )
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    classe = serializers.PrimaryKeyRelatedField(
        queryset=Classe.objects.all(),
        required=False,
        allow_null=True,
    )
    classe_name = serializers.SerializerMethodField()
    classe_field = serializers.SerializerMethodField()
    module_id = serializers.PrimaryKeyRelatedField(
        source="module",
        queryset=Module.objects.all(),
        required=False,
        allow_null=True,
    )
    module_name = serializers.CharField(source="module.name", read_only=True)
    
    block_name = serializers.CharField(source="block.name", read_only=True)
    block = serializers.PrimaryKeyRelatedField(
        queryset=Block.objects.all(),
        required=False,
        allow_null=True,
    )
    room_name = serializers.CharField(source="room.name", read_only=True)
    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
    )
    amphitheater_name = serializers.CharField(source="amphitheater.name", read_only=True)
    amphitheater = serializers.PrimaryKeyRelatedField(
        queryset=Amphitheater.objects.all(),
        required=False,
        allow_null=True,
    )
    is_qr_valid = serializers.BooleanField(read_only=True)
    is_within_session_window = serializers.BooleanField(read_only=True)
    can_generate_qr = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(default=True, required=False)
    is_closed = serializers.BooleanField(read_only=True)
    report_file = serializers.CharField(read_only=True)
    report_url = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user and getattr(user, "is_authenticated", False) and user.role == "teacher":
            self.fields["teacher"].required = False
            self.fields["teacher"].read_only = True
        if user and getattr(user, "is_authenticated", False) and user.role == "department_head":
            dept = user.headed_department.first()
            if dept:
                dept_classe_ids = Classe.objects.filter(
                    Q(department=dept) | Q(filiere__department=dept)
                ).values_list("id", flat=True).distinct()
                dept_module_ids = Module.objects.filter(filiere__department=dept).values_list("id", flat=True)
                dept_teacher_ids = User.objects.filter(
                    Q(role="teacher")
                    & (Q(assigned_classes__department=dept)
                       | Q(assigned_classes__filiere__department=dept)
                       | Q(sessions__classe__department=dept)
                       | Q(sessions__classe__filiere__department=dept)
                       | Q(taught_modules__filiere__department=dept))
                ).values_list("id", flat=True).distinct()
                self.fields["classe"].queryset = Classe.objects.filter(id__in=list(dept_classe_ids))
                self.fields["module_id"].queryset = Module.objects.filter(id__in=list(dept_module_ids))
                self.fields["teacher"].queryset = User.objects.filter(id__in=list(dept_teacher_ids))

    class Meta:
        model = Session
        fields = [
            "id",
            "subject",
            "module_id",
            "module_name",
            "teacher",
            "teacher_name",
            "classe",
            "classe_name",
            "classe_field",
            "location_type",
            "block",
            "block_name",
            "room",
            "room_name",
            "amphitheater",
            "amphitheater_name",
            "date",
            "start_time",
            "end_time",
            "qr_token",
            "qr_session_id",
            "qr_expires_at",
            "attendance_radius_meters",
            "location_latitude",
            "location_longitude",
            "is_active",
            "is_closed",
            "session_type",
            "report_file",
            "report_url",
            "is_qr_valid",
            "is_within_session_window",
            "can_generate_qr",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "module_name",
            "teacher_name",
            "block_name",
            "room_name",
            "amphitheater_name",
            "qr_token",
            "qr_session_id",
            "qr_expires_at",
            "attendance_radius_meters",
            "location_latitude",
            "location_longitude",
            "is_qr_valid",
            "is_within_session_window",
            "can_generate_qr",
            "report_file",
            "report_url",
            "created_at",
        ]
        extra_kwargs = {
            "date": {"required": True},
            "subject": {"required": False, "allow_blank": True},
        }

    def get_classe_name(self, obj):
        return str(obj.classe)

    def get_classe_field(self, obj):
        if not obj.classe:
            return "—"
        f = obj.classe.filiere
        return f.name if f else "—"

    def get_report_url(self, obj):
        if obj.report_file:
            return obj.report_file.url
        return None

    def validate(self, data):
        import logging
        logger = logging.getLogger(__name__)
        from django.utils import timezone

        logger.info(f"=== SessionSerializer.validate ===")
        logger.info(f"Input data: {data}")

        try:
            if not data.get("session_type"):
                data["session_type"] = "Cours"

            start_time = data.get("start_time", getattr(self.instance, "start_time", None))
            end_time = data.get("end_time", getattr(self.instance, "end_time", None))
            if start_time and end_time and end_time <= start_time:
                raise serializers.ValidationError(
                    {"end_time": "L'heure de fin doit être après l'heure de début."}
                )

            date_val = data.get("date", getattr(self.instance, "date", None))
            start_val = data.get("start_time", getattr(self.instance, "start_time", None))
            now = timezone.now()
            if date_val:
                if date_val < now.date():
                    raise serializers.ValidationError(
                        {"date": "Impossible de créer une séance avec une date passée."}
                    )
                if date_val == now.date() and start_val and start_val <= now.time():
                    raise serializers.ValidationError(
                        {"start_time": "L'heure de début ne peut pas être dans le passé."}
                    )

            module = data.get("module")
            subject = data.get("subject")

            if module and not subject:
                data["subject"] = module.name
            elif not subject:
                raise serializers.ValidationError(
                    {"subject": "La matière (subject) est obligatoire si aucun module n'est sélectionné."}
                )

            # Auto-resolve classe from module if not provided
            classe = data.get("classe", getattr(self.instance, "classe", None))
            if not classe and module:
                try:
                    filiere = module.filiere
                    if not filiere:
                        raise serializers.ValidationError(
                            {"module": "Le module sélectionné n'a pas de filière associée."}
                        )
                    today = timezone.now()
                    academic_year = f"{today.year}-{today.year + 1}"
                    # Auto-resolve Classe using only real Classe model fields
                    classe_name = f"{filiere.name}"
                    niveau = getattr(filiere, "niveau", None)
                    if not niveau:
                        raise serializers.ValidationError(
                            {"module": "Le module sélectionné n'a pas de niveau via la filière."}
                        )

                    existing = Classe.objects.filter(
                        niveau=niveau,
                        semestre=filiere.semestre,
                        filiere=filiere,
                        module=getattr(module, "pk", None) and module,
                    ).first()
                    if existing:
                        classe = existing
                    else:
                        classe = Classe.objects.create(
                            niveau=niveau,
                            semestre=filiere.semestre,
                            filiere=filiere,
                            module=getattr(module, "pk", None) and module,
                            name=classe_name,
                            academic_year=academic_year,
                            location_type="BLOC",
                        )
                    data["classe"] = classe
                    logger.info(f"Auto-resolved classe: {classe}")
                except Exception as e:
                    logger.error(f"Error auto-resolving classe: {str(e)}", exc_info=True)
                    raise serializers.ValidationError(
                        {"classe": f"Erreur lors de la création automatique de la classe: {str(e)}"}
                    )

            teacher = data.get("teacher", getattr(self.instance, "teacher", None))
            request = self.context.get("request")
            if request and request.user.role == "teacher" and classe:
                assigned = request.user.assigned_classes.filter(pk=classe.pk).exists()
                has_sessions = Session.objects.filter(
                    classe=classe, teacher=request.user
                ).exists()
                if not assigned and not has_sessions:
                    raise serializers.ValidationError(
                        {"classe": "Vous n'êtes pas affecté à cette classe."}
                    )
                if teacher and teacher.id != request.user.id:
                    raise serializers.ValidationError(
                        {"teacher": "Vous ne pouvez pas assigner une autre enseignant."}
                    )
            # Auto-assign teacher when a teacher creates the session
            if request and request.user.role == "teacher" and not data.get("teacher"):
                data["teacher"] = request.user

            # ── Room/Amphitheater conflict check ──
            location_type = data.get("location_type", getattr(self.instance, "location_type", None))
            date_val = data.get("date", getattr(self.instance, "date", None))
            st = data.get("start_time", getattr(self.instance, "start_time", None))
            et = data.get("end_time", getattr(self.instance, "end_time", None))
            exclude_id = self.instance.id if self.instance else None

            if location_type and date_val and st and et:
                from courses.utils import get_conflicting_sessions

                if location_type == "block":
                    room = data.get("room", getattr(self.instance, "room", None))
                    if room:
                        conflicts = get_conflicting_sessions(
                            date=date_val,
                            start_time=st,
                            end_time=et,
                            location_type="block",
                            room_id=room.id if hasattr(room, "id") else room,
                            exclude_session_id=exclude_id,
                        )
                        if conflicts.exists():
                            conflict = conflicts.first()
                            raise serializers.ValidationError(
                                f"Cette salle est déjà occupée par une autre séance "
                                f"entre {conflict.start_time.strftime('%H:%M')} et "
                                f"{conflict.end_time.strftime('%H:%M')}."
                            )
                elif location_type == "amphitheater":
                    amphi = data.get("amphitheater", getattr(self.instance, "amphitheater", None))
                    if amphi:
                        conflicts = get_conflicting_sessions(
                            date=date_val,
                            start_time=st,
                            end_time=et,
                            location_type="amphitheater",
                            amphitheater_id=amphi.id if hasattr(amphi, "id") else amphi,
                            exclude_session_id=exclude_id,
                        )
                        if conflicts.exists():
                            conflict = conflicts.first()
                            raise serializers.ValidationError(
                                f"Cet amphithéâtre est déjà occupé par une autre séance "
                                f"entre {conflict.start_time.strftime('%H:%M')} et "
                                f"{conflict.end_time.strftime('%H:%M')}."
                            )

            logger.info(f"Validation passed for SessionSerializer")
            return data
        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error in SessionSerializer.validate: {str(e)}", exc_info=True)
            raise serializers.ValidationError(
                {"detail": f"Erreur de validation: {str(e)}"}
            )


class GenerateQRSerializer(serializers.Serializer):
    expiry_minutes = serializers.IntegerField(min_value=1, max_value=120, default=20)
    attendance_radius_meters = serializers.IntegerField(
        min_value=20, max_value=200, default=50
    )
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
