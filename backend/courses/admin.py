from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import Session


# Choices for Niveau field
NIVEAU_CHOICES = [
    ("LIC", "Licence"),
    ("LIC_EXC", "Licence Excellence"),
    ("MAS", "Master"),
    ("MAS_EXC", "Master Parcours d'excellence"),
]

# Import the semestre/niveau map from users module
try:
    from users.models import NIVEAU_SEMESTRE_MAP
except ImportError:
    NIVEAU_SEMESTRE_MAP = {
        "LIC": frozenset(["S1", "S2", "S3", "S4", "S5", "S6"]),
        "LIC_EXC": frozenset(["S5", "S6"]),
        "MAS": frozenset(["S7", "S8", "S9", "S10"]),
        "MAS_EXC": frozenset(["S7", "S8", "S9", "S10"]),
    }


class SessionAdminForm(forms.ModelForm):
    """Custom form for Session with academic cascade validation."""

    class Meta:
        model = Session
        fields = "__all__"

    def clean(self):
        """Validate the academic combination: Niveau-Semestre-Filiere-Module."""
        cleaned_data = super().clean()
        niveau = cleaned_data.get("niveau")
        semestre = cleaned_data.get("semestre")
        filiere = cleaned_data.get("filiere")
        module = cleaned_data.get("module")

        # If all four fields are filled, check consistency
        if niveau and semestre and filiere and module:
            # Check that the filiere's niveau matches the selected niveau
            if filiere.niveau != niveau:
                raise ValidationError(
                    {"niveau": f"La filière '{filiere.name}' ne correspond pas au niveau '{niveau}'."}
                )
            # Check that the filiere's semestre matches the selected semestre
            if filiere.semestre_id != semestre.id:
                raise ValidationError(
                    {"semestre": f"La filière '{filiere.name}' n'est pas associée au semestre '{semestre.name}'."}
                )
            # Check that the module belongs to the selected filiere
            if module.filiere_id != filiere.id:
                raise ValidationError(
                    {"module": f"Le module '{module.name}' ne appartient pas à la filière '{filiere.name}'."}
                )
            # Check that the semestre is allowed for the niveau
            # using the NIVEAU_SEMESTRE_MAP
            allowed_sems = NIVEAU_SEMESTRE_MAP.get(niveau, frozenset())
            if allowed_sems and semestre.name not in allowed_sems:
                raise ValidationError(
                    {"semestre": f"Le semestre '{semestre.name}' n'est pas autorisé pour le niveau '{niveau}'."}
                )
        # If module is set without niveau/semestre/filiere, skip cross-validation
        # (the module alone determines some constraints)
        # If niveau/semestre/filiere are set but module is not, that's OK (optional module)

        return cleaned_data


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin for Session with academic cascade filtering."""

    form = SessionAdminForm

    list_display = [
        "subject",
        "classe",
        "niveau",
        "semestre",
        "filiere",
        "module",
        "teacher",
        "date",
        "is_active",
    ]
    list_filter = ["is_active", "classe", "teacher", "niveau", "semestre", "filiere", "module"]
    search_fields = ["subject", "classe__name", "module__name", "filiere__name", "semestre__name"]
    readonly_fields = ["qr_token", "qr_expires_at", "created_at"]

    fieldsets = (
        (None, {"fields": ("subject", "module", "teacher", "classe")}),
        ("Configuration académique", {
            "fields": ("niveau", "semestre", "filiere"),
            "classes": ["wide"],
        }),
        ("Lieu et horaire", {"fields": ("location_type", "block", "room", "amphitheater", "date", "start_time", "end_time")}),
        ("Type de séance", {"fields": ("session_type",)}),
        ("QR Code", {"fields": ("qr_token", "qr_expires_at", "attendance_radius_meters", "location_latitude", "location_longitude"), "classes": ["collapse"]}),
        ("Gestion", {"fields": ("is_active", "is_closed", "report_file"), "classes": ["collapse"]}),
    )

    def get_form(self, request, obj=None, change=False):
        """Customize the form for the admin."""
        return SessionAdminForm

    class Media:
        js = ("/session-form.js",)

    def save_model(self, request, obj, form, change):
        """Save the model with academic combination validation."""
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            raise Exception(str(e))