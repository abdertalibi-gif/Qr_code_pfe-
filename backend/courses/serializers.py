from datetime import time, timedelta

from django.db.models import Q
from rest_framework import serializers

from attendance.utils import round_coordinate
from curriculum.models import Filiere, Module, Semestre
from users.models import Classe, User, Block, Room, Amphitheater
from users.permissions import get_user_filiere_ids

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
    title = serializers.CharField(source="subject", read_only=True)
    class_name = serializers.SerializerMethodField()
    matiere_name = serializers.CharField(source="module.name", read_only=True)
    status = serializers.SerializerMethodField()
    module_id = serializers.PrimaryKeyRelatedField(
        source="module",
        queryset=Module.objects.all(),
        required=False,
        allow_null=True,
    )
    module_name = serializers.CharField(source="module.name", read_only=True)
    niveau = serializers.ChoiceField(
        choices=Session.NIVEAU_CHOICES,
        required=False,
        allow_blank=True,
    )
    semestre_id = serializers.PrimaryKeyRelatedField(
        source="semestre",
        queryset=Semestre.objects.all(),
        required=False,
        allow_null=True,
    )
    semestre_name = serializers.CharField(source="semestre.name", read_only=True)
    filiere_id = serializers.PrimaryKeyRelatedField(
        source="filiere",
        queryset=Filiere.objects.all(),
        required=False,
        allow_null=True,
    )
    filiere_name = serializers.CharField(source="filiere.name", read_only=True)
    
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
    exclude_session_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        is_write = "data" in kwargs or (request and getattr(request, "method", None) in ("POST", "PUT", "PATCH"))
        if user and getattr(user, "is_authenticated", False) and user.role == "teacher":
            self.fields["teacher"].required = False
            self.fields["teacher"].read_only = True
        if is_write and user and getattr(user, "is_authenticated", False) and user.role == "department_head":
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
        if is_write and user and getattr(user, "is_authenticated", False) and user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(user)
            if filiere_ids:
                pm_classe_ids = Classe.objects.filter(filiere_id__in=filiere_ids).values_list("id", flat=True).distinct()
                pm_module_ids = Module.objects.filter(filiere_id__in=filiere_ids).values_list("id", flat=True)
                pm_teacher_ids = User.objects.filter(
                    Q(role="teacher")
                    & (Q(assigned_classes__filiere_id__in=filiere_ids)
                       | Q(sessions__classe__filiere_id__in=filiere_ids)
                       | Q(taught_modules__filiere_id__in=filiere_ids))
                ).values_list("id", flat=True).distinct()
                self.fields["classe"].queryset = Classe.objects.filter(id__in=list(pm_classe_ids))
                self.fields["module_id"].queryset = Module.objects.filter(id__in=list(pm_module_ids))
                self.fields["teacher"].queryset = User.objects.filter(id__in=list(pm_teacher_ids))

    class Meta:
        model = Session
        fields = [
            "id",
            "title",
            "subject",
            "module_id",
            "module_name",
            "matiere_name",
            "niveau",
            "semestre_id",
            "semestre_name",
            "filiere_id",
            "filiere_name",
            "teacher",
            "teacher_name",
            "classe",
            "classe_name",
            "class_name",
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
            "status",
            "is_active",
            "is_closed",
            "session_type",
            "report_file",
            "report_url",
            "is_qr_valid",
            "is_within_session_window",
            "can_generate_qr",
            "created_at",
            "exclude_session_ids",
        ]
        read_only_fields = [
            "id",
            "title",
            "module_name",
            "matiere_name",
            "semestre_name",
            "filiere_name",
            "teacher_name",
            "classe_name",
            "class_name",
            "status",
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
            "date": {"required": False},
            "subject": {"required": False, "allow_blank": True},
        }

    def get_classe_name(self, obj):
        return str(obj.classe) if obj.classe else "—"

    def get_class_name(self, obj):
        return str(obj.classe) if obj.classe else "—"

    def get_status(self, obj):
        if obj.is_closed:
            return "completed"
        return "active" if obj.is_active else "inactive"

    def get_classe_field(self, obj):
        if not obj.classe:
            return "—"
        f = obj.classe.filiere
        return f.name if f else "—"

    def get_report_url(self, obj):
        if obj.report_file:
            return obj.report_file.url
        return None

    def _validate_academic_combination(self, data):
        """Re-vérifie côté serveur la cohérence Niveau → Semestre → Filière → Module.

        Les relations Django réelles sont utilisées (Filiere.niveau,
        Filiere.semestre, Module.filiere) : toute combinaison incohérente est
        refusée même si les valeurs ont été modifiées dans le navigateur.
        """
        from users.models import NIVEAU_SEMESTRE_MAP

        instance = self.instance

        def _current(key, attr):
            if key in data:
                return data.get(key)
            return getattr(instance, attr, None) if instance else None

        niveau = _current("niveau", "niveau") or ""
        semestre = _current("semestre", "semestre")
        filiere = _current("filiere", "filiere")
        module = _current("module", "module")

        # Aucun champ académique fourni : rien à valider (compatibilité API).
        if not any(k in data for k in ("niveau", "semestre", "filiere", "module")):
            return data

        # Complète les valeurs manquantes à partir des relations réelles.
        if module is not None:
            if filiere is None and module.filiere_id:
                filiere = module.filiere
            if semestre is None and filiere is not None:
                semestre = filiere.semestre
            if not niveau and filiere is not None:
                niveau = filiere.niveau

        errors = {}

        if filiere is not None:
            if niveau and filiere.niveau != niveau:
                errors["filiere_id"] = (
                    f"La filière '{filiere.name}' ne correspond pas au niveau sélectionné."
                )
            if semestre is not None and filiere.semestre_id != semestre.id:
                errors["semestre_id"] = (
                    f"La filière '{filiere.name}' n'est pas associée au semestre "
                    f"'{semestre.name}'."
                )

        if module is not None and filiere is not None and module.filiere_id != filiere.id:
            errors["module_id"] = (
                f"Le module '{module.name}' n'appartient pas à la filière "
                f"'{filiere.name}'."
            )

        if niveau and semestre is not None:
            allowed = NIVEAU_SEMESTRE_MAP.get(niveau)
            if allowed is not None and semestre.name not in allowed:
                errors["semestre_id"] = (
                    f"Le semestre '{semestre.name}' n'est pas autorisé pour ce niveau."
                )

        # Cohérence avec la classe cible lorsqu'elle est fournie.
        classe = data.get("classe", getattr(instance, "classe", None) if instance else None)
        if classe is not None:
            if filiere is not None and classe.filiere_id and classe.filiere_id != filiere.id:
                errors["classe"] = (
                    "La classe sélectionnée n'appartient pas à la filière choisie."
                )
            if semestre is not None and classe.semestre_id and classe.semestre_id != semestre.id:
                errors["classe"] = (
                    "La classe sélectionnée n'appartient pas au semestre choisi."
                )
            if niveau and classe.niveau and classe.niveau != niveau:
                errors["classe"] = (
                    "La classe sélectionnée n'appartient pas au niveau choisi."
                )

        if errors:
            raise serializers.ValidationError(errors)
        return data

    def validate(self, data):
        import logging
        logger = logging.getLogger(__name__)
        from django.utils import timezone

        logger.info(f"=== SessionSerializer.validate ===")
        logger.info(f"Input data: {data}")

        try:
            if not data.get("session_type"):
                data["session_type"] = "Cours"

            # Validation stricte de la combinaison académique (relations réelles).
            data = self._validate_academic_combination(data)

            # Création : la séance démarre immédiatement. La date et l'heure de
            # début sont imposées par le serveur ; toute valeur envoyée par le
            # client est ignorée.
            is_create = self.instance is None
            if is_create:
                now_local = timezone.localtime()
                data["date"] = now_local.date()
                data["start_time"] = now_local.time().replace(microsecond=0)
                if not data.get("end_time"):
                    # Aucune heure de fin fournie : créneau par défaut de 2 h.
                    default_end = now_local + timedelta(hours=2)
                    if default_end.date() != now_local.date():
                        data["end_time"] = time(23, 59)
                    else:
                        data["end_time"] = default_end.time().replace(microsecond=0)

            start_time = data.get("start_time", getattr(self.instance, "start_time", None))
            end_time = data.get("end_time", getattr(self.instance, "end_time", None))
            if start_time and end_time and end_time <= start_time:
                raise serializers.ValidationError(
                    {"end_time": "L'heure de fin doit être après l'heure de début."}
                )

            date_val = data.get("date", getattr(self.instance, "date", None))
            start_val = data.get("start_time", getattr(self.instance, "start_time", None))
            # Édition : si la date et l'heure de début n'ont pas changé, on
            # autorise la modification même si la séance a déjà commencé
            # (ex. corriger l'heure de fin ou le type de séance).
            unchanged_start = (
                not is_create
                and self.instance is not None
                and date_val == self.instance.date
                and start_val is not None
                and start_val.replace(second=0, microsecond=0)
                == self.instance.start_time.replace(second=0, microsecond=0)
            )
            if unchanged_start:
                # Le formulaire ne renvoie que HH:MM alors que la séance a été
                # créée avec des secondes : on conserve l'heure réelle et on
                # autorise la modification d'une séance déjà commencée.
                data.pop("start_time", None)
            if not is_create and date_val and not unchanged_start:
                now = timezone.now()
                if date_val < now.date():
                    raise serializers.ValidationError(
                        {"date": "Impossible de repérer une séance avec une date passée."}
                    )
                if date_val == now.date() and start_val and start_val <= now.time():
                    raise serializers.ValidationError(
                        {"start_time": "L'heure de début ne peut pas être dans le passé."}
                    )

            module = data.get("module", getattr(self.instance, "module", None))
            subject = data.get("subject", getattr(self.instance, "subject", None))

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

            # Lieu par défaut de la classe (défini par l'administrateur) si aucun
            # lieu n'est fourni — création uniquement (l'édition préserve le lieu existant).
            if not data.get("location_type") and classe and not self.instance:
                cls_loc = classe.location_type
                if cls_loc in ("BLOC", "BOTH_ALLOWED") and classe.block_id and classe.room_id:
                    data["location_type"] = "block"
                    data["block"] = classe.block
                    data["room"] = classe.room
                elif cls_loc in ("AMPHI", "BOTH_ALLOWED") and classe.amphitheater_id:
                    data["location_type"] = "amphitheater"
                    data["amphitheater"] = classe.amphitheater

            teacher = data.get("teacher", getattr(self.instance, "teacher", None))
            request = self.context.get("request")
            if request and request.user.role == "teacher" and classe:
                assigned = request.user.assigned_classes.filter(pk=classe.pk).exists()
                if not assigned:
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

            # ── Teacher time-overlap check ──
            # Un enseignant ne peut pas avoir deux séances qui se chevauchent
            # sur la même date. Les séances clôturées sont ignorées.
            teacher_for_check = data.get(
                "teacher", getattr(self.instance, "teacher", None)
            )
            teacher_date = data.get("date", getattr(self.instance, "date", None))
            teacher_start = data.get(
                "start_time", getattr(self.instance, "start_time", None)
            )
            teacher_end = data.get(
                "end_time", getattr(self.instance, "end_time", None)
            )
            if teacher_for_check and teacher_date and teacher_start and teacher_end:
                from courses.utils import (
                    TEACHER_SESSION_OVERLAP_MESSAGE,
                    get_teacher_conflicting_sessions,
                )

                teacher_conflicts = get_teacher_conflicting_sessions(
                    teacher_id=teacher_for_check.pk,
                    date=teacher_date,
                    start_time=teacher_start,
                    end_time=teacher_end,
                    exclude_session_id=self.instance.pk if self.instance else None,
                )
                if teacher_conflicts.exists():
                    raise serializers.ValidationError(
                        TEACHER_SESSION_OVERLAP_MESSAGE
                    )

            # ── Room/Amphitheater conflict check ──
            location_type = data.get("location_type", getattr(self.instance, "location_type", None))
            date_val = data.get("date", getattr(self.instance, "date", None))
            st = data.get("start_time", getattr(self.instance, "start_time", None))
            et = data.get("end_time", getattr(self.instance, "end_time", None))
            exclude_id = self.instance.id if self.instance else None

            if location_type and date_val and st and et:
                from courses.utils import get_conflicting_sessions

                # Séances créées dans la même opération multi-classes : le front les
                # transmet via `exclude_session_ids` pour qu'elles ne déclenchent pas
                # de faux conflit de salle (même enseignant/module/créneau/lieu/type).
                # Un conflit réel avec une séance hors du lot reste bloqué.
                provided_excludes = data.pop("exclude_session_ids", None) or []
                exclude_ids = {i for i in provided_excludes if isinstance(i, int)}
                if exclude_id:
                    exclude_ids.add(exclude_id)

                def _apply_excludes(qs):
                    if exclude_ids:
                        qs = qs.exclude(id__in=list(exclude_ids))
                    return qs

                if location_type == "block":
                    room = data.get("room", getattr(self.instance, "room", None))
                    if room:
                        conflicts = _apply_excludes(
                            get_conflicting_sessions(
                                date=date_val,
                                start_time=st,
                                end_time=et,
                                location_type="block",
                                room_id=room.id if hasattr(room, "id") else room,
                                exclude_session_id=exclude_id,
                            )
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
                        conflicts = _apply_excludes(
                            get_conflicting_sessions(
                                date=date_val,
                                start_time=st,
                                end_time=et,
                                location_type="amphitheater",
                                amphitheater_id=amphi.id if hasattr(amphi, "id") else amphi,
                                exclude_session_id=exclude_id,
                            )
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
