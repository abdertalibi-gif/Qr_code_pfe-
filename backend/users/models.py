from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

ROLE_CHOICES = [
    ("admin", "Admin"),
    ("teacher", "Enseignant"),
    ("student", "Étudiant"),
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

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


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
