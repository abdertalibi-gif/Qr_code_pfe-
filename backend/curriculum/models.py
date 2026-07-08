from django.db import models


NIVEAU_CHOICES = [
    ("LIC", "Licence"),
    ("LIC_EXC", "Licence Excellence"),
    ("MAS", "Master"),
    ("MAS_EXC", "Master Parcours d'excellence"),
]


class Semestre(models.Model):
    """Semestre académique (S1, S2, S3, ...)"""
    name = models.CharField(max_length=10, unique=True, verbose_name="Semestre")

    class Meta:
        db_table = "semestres"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Filiere(models.Model):
    """Filière académique (L1 Informatique, L2 Informatique, etc.)"""
    name = models.CharField(max_length=100, verbose_name="Filière")
    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.CASCADE,
        related_name="filieres",
        verbose_name="Semestre"
    )
    niveau = models.CharField(
        max_length=10,
        verbose_name="Niveau",
        choices=NIVEAU_CHOICES,
        blank=True,
        default="",
    )
    department = models.ForeignKey(
        "users.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="filieres",
        verbose_name="Département",
    )
    manager = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_filieres",
        verbose_name="Responsable de filière",
    )

    class Meta:
        db_table = "filieres"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["semestre", "niveau"], name="idx_filiere_sem_niv"),
        ]

    def __str__(self):
        return self.name


class Module(models.Model):
    """Module académique (Algorithmique, Math, etc.)"""
    name = models.CharField(max_length=200, verbose_name="Module")
    filiere = models.ForeignKey(
        Filiere,
        on_delete=models.CASCADE,
        related_name="modules",
        verbose_name="Filière"
    )

    class Meta:
        db_table = "modules"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["filiere"], name="idx_module_filiere"),
        ]

    def __str__(self):
        return self.name
