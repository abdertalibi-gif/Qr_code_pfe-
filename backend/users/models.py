from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

ROLE_CHOICES = [
    ("admin", "Admin"),
    ("teacher", "Enseignant"),
    ("student", "Étudiant"),
    ("department_head", "Chef de département"),
    ("program_manager", "Responsable de filière"),
]


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="teacher")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_classes = models.ManyToManyField(
        "Classe",
        blank=True,
        related_name="teachers",
        help_text="Classes assignées (enseignants uniquement).",
    )
    is_also_teacher = models.BooleanField(default=False)
    phone = models.CharField(max_length=30, blank=True, default="")
    cin = models.CharField(max_length=30, blank=True, default="", null=True)
    grade = models.CharField(max_length=100, blank=True, default="")
    speciality = models.CharField(max_length=200, blank=True, default="")
    department = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachers",
        verbose_name="Département",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        constraints = [
            # Un CIN ne peut appartenir qu'à un seul étudiant. Les valeurs
            # vides restent autorisées (comptes non étudiants, CIN inconnu).
            models.UniqueConstraint(
                fields=["cin"],
                condition=(
                    Q(role="student")
                    & Q(cin__isnull=False)
                    & ~Q(cin="")
                ),
                name="uniq_student_user_cin",
            ),
            # Les emails étudiants sont uniques sans distinction de casse.
            # La contrainte exacte globale sur `email` reste en place.
            models.UniqueConstraint(
                Lower("email"),
                condition=Q(role="student"),
                name="uniq_student_user_email_ci",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.cin:
            self.cin = self.cin.strip()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.email = (self.email or "").strip().lower()
        self.cin = (self.cin or "").strip()

        if self.role != "student":
            return

        if self.cin:
            duplicate = (
                User.objects.filter(role="student", cin__iexact=self.cin)
                .exclude(pk=self.pk)
                .first()
            )
            if duplicate:
                raise ValidationError(
                    {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                )

        if self.email:
            duplicate = (
                User.objects.filter(role="student", email__iexact=self.email)
                .exclude(pk=self.pk)
                .first()
            )
            if duplicate:
                raise ValidationError(
                    {"email": "Cette adresse e-mail est déjà utilisée par un autre étudiant."}
                )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Department(models.Model):
    """Département académique (Mathématiques, Informatique, etc.)"""
    name = models.CharField(max_length=200, verbose_name="Département")
    head = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_department",
        verbose_name="Chef de département",
    )

    class Meta:
        managed = False
        db_table = "departments"
        ordering = ["name"]
        verbose_name = "Département"
        verbose_name_plural = "Départements"

    def __str__(self):
        return self.name


class Block(models.Model):
    """Bloc physique (Bloc 1, Bloc 2, ...)"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Bloc")

    class Meta:
        db_table = "blocks"
        ordering = ["name"]
        verbose_name = "Bloc"
        verbose_name_plural = "Blocs"

    def __str__(self):
        return self.name


class Room(models.Model):
    """Salle dans un bloc (Salle 1, Salle 2, ...)"""
    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name="rooms",
        verbose_name="Bloc",
    )
    name = models.CharField(max_length=50, verbose_name="Salle")

    class Meta:
        db_table = "rooms"
        ordering = ["block__name", "name"]
        verbose_name = "Salle"
        verbose_name_plural = "Salles"
        constraints = [
            models.UniqueConstraint(
                fields=["block", "name"],
                name="uniq_block_room",
            )
        ]

    def __str__(self):
        return f"{self.block.name} - {self.name}"


class Amphitheater(models.Model):
    """Amphithéâtre (Amphi A, Amphi B, ...)"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Amphithéâtre")

    class Meta:
        db_table = "amphitheaters"
        ordering = ["name"]
        verbose_name = "Amphithéâtre"
        verbose_name_plural = "Amphithéâtres"

    def __str__(self):
        return self.name


NIVEAU_CLASSE_CHOICES = [
    ("LIC", "Licence"),
    ("LIC_EXC", "Licence Excellence"),
    ("MAS", "Master"),
    ("MAS_EXC", "Master Parcours d'excellence"),
]

LOCATION_TYPE_CHOICES = [
    ("BLOC", "Bloc + Salle"),
    ("AMPHI", "Amphithéâtre"),
    ("BOTH_ALLOWED", "Bloc + Amphi (les deux)"),
]

NIVEAU_SEMESTRE_MAP = {
    "LIC": frozenset(["S1", "S2", "S3", "S4", "S5", "S6"]),
    "LIC_EXC": frozenset(["S5", "S6"]),
    "MAS": frozenset(["S7", "S8", "S9", "S10"]),
    "MAS_EXC": frozenset(["S7", "S8", "S9", "S10"]),
}


class AcademicYear(models.Model):
    """Année universitaire de référence."""
    label = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "academic_years"
        verbose_name = "Année universitaire"
        verbose_name_plural = "Années universitaires"

    def __str__(self):
        return self.label


class Group(models.Model):
    """Groupe d'étudiants."""
    name = models.CharField(max_length=200)
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE,
        related_name="groups",
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="groups",
    )

    class Meta:
        managed = False
        db_table = "groups"
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"

    def __str__(self):
        return self.name


class Faculty(models.Model):
    """Faculté."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        managed = False
        db_table = "faculties"
        verbose_name = "Faculté"
        verbose_name_plural = "Facultés"

    def __str__(self):
        return self.name


class Classe(models.Model):
    """Groupe d'étudiants (niveau, filière, semestre, année universitaire)."""

    name = models.CharField(max_length=200, verbose_name="Nom", blank=True, default="")
    code = models.CharField(max_length=30, blank=True, default="", verbose_name="Code")
    niveau = models.CharField(
        max_length=10,
        verbose_name="Niveau",
        choices=NIVEAU_CLASSE_CHOICES,
        default="",
    )
    filiere = models.ForeignKey(
        "curriculum.Filiere",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Filière",
        help_text="Lier à une filière du curriculum"
    )
    semestre = models.ForeignKey(
        "curriculum.Semestre",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Semestre",
    )
    module = models.ForeignKey(
        "curriculum.Module",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Module",
    )
    academic_year = models.CharField(max_length=20, verbose_name="Année universitaire")
    location_type = models.CharField(
        max_length=20,
        verbose_name="Type de localisation",
        choices=LOCATION_TYPE_CHOICES,
        default="BLOC",
    )
    block = models.ForeignKey(
        Block,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Bloc",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Salle",
    )
    amphitheater = models.ForeignKey(
        Amphitheater,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Amphithéâtre",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Département",
    )
    group = models.ForeignKey(
        "Group",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Groupe",
    )
    academic_year_ref = models.ForeignKey(
        "AcademicYear",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
        verbose_name="Année universitaire (réf)",
    )
    level = models.CharField(max_length=50, blank=True, default="", verbose_name="Niveau (legacy)")
    field = models.CharField(max_length=100, blank=True, default="", verbose_name="Domaine (legacy)")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "classes"
        ordering = ["-created_at"]
        verbose_name = "Classe"
        verbose_name_plural = "Classes"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self._generate_name()
        super().save(*args, **kwargs)

    def _generate_name(self):
        parts = []
        if self.filiere:
            parts.append(self.filiere.name)
        if self.semestre:
            parts.append(self.semestre.name)
        if self.academic_year:
            parts.append(self.academic_year)
        return " - ".join(parts) if parts else "Classe"

    def __str__(self):
        return self.name or self._generate_name()

    def location_display(self):
        if self.location_type in ("BLOC", "BOTH_ALLOWED") and self.block and self.room:
            bloc = f"{self.block.name} - {self.room.name}"
            if self.location_type == "BOTH_ALLOWED" and self.amphitheater:
                return f"{bloc} / {self.amphitheater.name}"
            return bloc
        elif self.location_type in ("AMPHI", "BOTH_ALLOWED") and self.amphitheater:
            if self.location_type == "BOTH_ALLOWED" and self.block and self.room:
                return f"{self.block.name} - {self.room.name} / {self.amphitheater.name}"
            return self.amphitheater.name
        return "—"


class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="student_profile",
        limit_choices_to={"role": "student"},
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    code_massar = models.CharField(max_length=50, unique=True)
    code_apogee = models.CharField(max_length=50, blank=True, null=True, verbose_name="Code Apogée")
    cin = models.CharField(max_length=30, blank=True, default="", null=True, verbose_name="CIN / CNI")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name="students",
    )
    modules = models.ManyToManyField(
        "curriculum.Module",
        through="StudentModuleEnrollment",
        related_name="students",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "students"
        constraints = [
            # Le CNE (code Massar) est déjà unique via `unique=True`.
            # Le CIN doit être unique parmi les étudiants, hors valeur vide.
            models.UniqueConstraint(
                fields=["cin"],
                condition=Q(cin__isnull=False) & ~Q(cin=""),
                name="uniq_student_cin",
            ),
            # Email unique sans distinction de casse, hors valeur vide.
            models.UniqueConstraint(
                Lower("email"),
                condition=~Q(email=""),
                name="uniq_student_profile_email_ci",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.code_massar:
            self.code_massar = self.code_massar.strip()
        if self.code_apogee:
            self.code_apogee = self.code_apogee.strip()
        if self.cin:
            self.cin = self.cin.strip()
        if self.email:
            self.email = self.email.strip().lower()
        if self.phone:
            self.phone = self.phone.strip()

        # Conserver la fiche utilisateur alignée pour les écrans qui lisent
        # encore `user.cin` (profil, administration).
        if self.cin and self.user_id and self.user.cin != self.cin:
            self.user.cin = self.cin
            self.user.save(update_fields=["cin"])

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.code_massar = (self.code_massar or "").strip()
        self.cin = (self.cin or "").strip()
        self.email = (self.email or "").strip().lower()

        if not self.code_massar:
            raise ValidationError(
                {"code_massar": "Le CNE (code Massar) est obligatoire."}
            )

        duplicate_code = (
            Student.objects.filter(code_massar__iexact=self.code_massar)
            .exclude(pk=self.pk)
            .first()
        )
        if duplicate_code:
            raise ValidationError(
                {
                    "code_massar": (
                        "Ce CNE (code Massar) est déjà utilisé par "
                        f"{duplicate_code.first_name} {duplicate_code.last_name}."
                    )
                }
            )

        if self.cin:
            duplicate_cin = (
                Student.objects.filter(cin__iexact=self.cin)
                .exclude(pk=self.pk)
                .first()
            )
            if duplicate_cin:
                raise ValidationError(
                    {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                )

            duplicate_user_cin = (
                User.objects.filter(role="student", cin__iexact=self.cin)
                .exclude(pk=self.user_id)
                .first()
            )
            if duplicate_user_cin:
                raise ValidationError(
                    {"cin": "Ce CIN est déjà utilisé par un autre étudiant."}
                )

        if self.email:
            duplicate_email = (
                Student.objects.filter(email__iexact=self.email)
                .exclude(pk=self.pk)
                .first()
            )
            if duplicate_email:
                raise ValidationError(
                    {"email": "Cette adresse e-mail est déjà utilisée par un autre étudiant."}
                )

            duplicate_user_email = (
                User.objects.filter(email__iexact=self.email)
                .exclude(pk=self.user_id)
                .first()
            )
            if duplicate_user_email:
                raise ValidationError(
                    {"email": "Cette adresse e-mail est déjà utilisée par un autre compte."}
                )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.code_massar})"


class StudentModuleEnrollment(models.Model):
    """Inscription d'un étudiant à un module (table de liaison M2M)."""

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="module_enrollments",
    )
    module = models.ForeignKey(
        "curriculum.Module",
        on_delete=models.CASCADE,
        related_name="student_enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_module"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "module"],
                name="uniq_student_module_enrollment",
            )
        ]
        indexes = [
            models.Index(fields=["module", "student"]),
        ]

    def __str__(self):
        return f"{self.student.code_massar} → {self.module.name}"
