"""
Assign department heads and program managers from official FS-UMI website data.
Run: python assign_heads_managers.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()

from users.models import User, Department
from curriculum.models import Filiere

# ── Department heads ─────────────────────────────────────────────────
DEPARTMENT_HEADS = {
    "Biologie":      ("Lhoussain", "HAJJI",     "l.hajji@umi.ac.ma"),
    "Chimie":        ("Ali",       "AMECHROUQ",  "a.amachrouq@umi.ac.ma"),
    "Géologie":      ("Houssa",    "OUALI",      "h.ouali@umi.ac.ma"),
    "Mathématiques": ("Mohamed",   "RHOUDAF",    "m.rhoudaf@umi.ac.ma"),
    "Physique":      ("Mohammed",  "KHALIS",     "m.khalis@umi.ac.ma"),
    # Informatique: no head listed on official site
}

# ── Program managers ─────────────────────────────────────────────────
# Filiere name → (first_name, last_name, email)
PROGRAM_MANAGERS = {
    "Digitalisation":                                    ("Hamid",      "BOURRAY",              "h.bourray@umi.ac.ma"),
    "Genie Informatique":                                ("Ali",        "OUBELKACEM",           "a.oubelkacem@umi.ac.ma"),
    "Intelligence et Securite des Objets Connectes":     ("Abdelbaki",  "EL BELRHITI EL ALAOUI","a.elbelrhitielalaoui@umi.ac.ma"),
    "Intelligence et Sécurité des Objets Connectés":     ("Abdelbaki",  "EL BELRHITI EL ALAOUI","a.elbelrhitielalaoui@umi.ac.ma"),
    "Systemes Intelligents et Recherche Operationnelle": ("Khalid",     "EL YASSINI",           "k.elyassini@umi.ac.ma"),
    "Systèmes Intelligents et Recherche Opérationnelle": ("Khalid",     "EL YASSINI",           "k.elyassini@umi.ac.ma"),
    "Sciences des Donnees et Intelligence Artificielle": ("Ali",        "BEKRI",                "a.bekri@umi.ac.ma"),
    "Sciences des données et Intelligence Artificielle": ("Ali",        "BEKRI",                "a.bekri@umi.ac.ma"),
    "Intelligence Artificielle & Recherche Opérationnelle": ("Khalid",  "EL YASSINI",           "k.elyassini@umi.ac.ma"),
    "Intelligence Artificielle et Recherche Operationnelle": ("Khalid", "EL YASSINI",           "k.elyassini@umi.ac.ma"),
    "Intelligence Artificielle et Systèmes de Décisions Optimales": ("", "", ""),
    "Intelligence Artificielle et Systemes de Decisions Optimales": ("", "", ""),
    "Mathematiques et Applications":                    ("Driss",      "SEGHIR",               "d.seghir@umi.ac.ma"),
    "Mathématiques et Applications":                    ("Driss",      "SEGHIR",               "d.seghir@umi.ac.ma"),
    "Electronique et Systemes":                         ("Mohamed",    "EL AMRAOUI",           "m.elamraoui@umi.ac.ma"),
    "Électronique et Systèmes":                         ("Mohamed",    "EL AMRAOUI",           "m.elamraoui@umi.ac.ma"),
    "Materiaux et Energetique":                         ("Ismail",     "ESSAOUDI",             "i.essaoudi@umi.ac.ma"),
    "Matériaux et Énergétique":                         ("Ismail",     "ESSAOUDI",             "i.essaoudi@umi.ac.ma"),
    "Mecanique des Fluides et Energetique":             ("", "", ""),
    "Mécanique des Fluides et Énergétique":             ("", "", ""),
    "Physique Appliquee et Ingenierie Physique":        ("", "", ""),
    "Physique Appliquée et Ingénierie Physique":        ("", "", ""),
    "Plasturgie et Ingenierie Biomedicale":             ("", "", ""),
    "Plasturgie et Ingénierie Biomédicale":             ("", "", ""),
    "Chimie Organique et Bioorganique":                 ("Noureddine", "ELMOUALIJ",            "n.elmoualij@umi.ac.ma"),
    "Chimie Physique Appliquee et Environnement":       ("Rachid",     "CHFAIRA",              "r.chfaira@umi.ac.ma"),
    "Chimie Physique Appliquée et Environnement":       ("Rachid",     "CHFAIRA",              "r.chfaira@umi.ac.ma"),
    "Chimie des Materiaux et des Procedes Industriels": ("Fatima",     "BOUKHLIFI",            "f.boukhlifi@umi.ac.ma"),
    "Chimie des Matériaux et des Procédés Industriels": ("Fatima",     "BOUKHLIFI",            "f.boukhlifi@umi.ac.ma"),
    "Biologie Cellulaire et Physiologie Humaine":       ("Hassan",     "HAJJAJ",               "h.hajjaj@umi.ac.ma"),
    "BioActifs, Sante et Environnement":                ("Younes",     "FILALI-ZEGZOUTI",      "y.filalizegzouti@umi.ac.ma"),
    "BioActifs, Santé et Environnement":                ("Younes",     "FILALI-ZEGZOUTI",      "y.filalizegzouti@umi.ac.ma"),
    "Geosciences et Geologie de l'Ingenieur":           ("Abdelilah",  "DEKAYIR",              "a.dekayir@umi.ac.ma"),
    "Géosciences et Géologie de l'Ingénieur":           ("Abdelilah",  "DEKAYIR",              "a.dekayir@umi.ac.ma"),
    "Hydrologie et Hydrogeologie":                      ("El mostafa", "MILI",                 "e.mili@umi.ac.ma"),
    "Hydrologie et Hydrogéologie":                      ("El mostafa", "MILI",                 "e.mili@umi.ac.ma"),
    "Geodynamique et Georessources":                    ("Houssa",     "OUALI",                "h.ouali@umi.ac.ma"),
    "Géodynamique et Géoressources":                    ("Houssa",     "OUALI",                "h.ouali@umi.ac.ma"),
}

# ── Helpers ──────────────────────────────────────────────────────────

def get_or_create_user(first_name, last_name, email, role):
    if not email:
        return None
    user = User.objects.filter(email=email).first()
    if user:
        if user.role not in (role, "admin"):
            print(f"  [WARN] User {email} exists with role={user.role}, updating to {role}")
            user.role = role
            user.is_also_teacher = True
            user.save()
        return user
    user = User.objects.create_user(
        email=email,
        password="changeme123",
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_also_teacher=True,
    )
    print(f"  [OK] Created {role}: {first_name} {last_name} <{email}>")
    return user


def assign_heads():
    print("=" * 60)
    print("ASSIGNING DEPARTMENT HEADS")
    print("=" * 60)
    for dept_name, (fn, ln, email) in DEPARTMENT_HEADS.items():
        dept = Department.objects.filter(name=dept_name).first()
        if not dept:
            print(f"  ✗ Department '{dept_name}' not found")
            continue
        user = get_or_create_user(fn, ln, email, "department_head")
        if user:
            dept.head = user
            dept.save()
            print(f"  → {dept_name}.head_id = {user.id} ({fn} {ln})")
    # Informatique – no head found
    print("  ℹ Informatique: no head listed on official site → left NULL")


def assign_managers():
    print()
    print("=" * 60)
    print("ASSIGNING PROGRAM MANAGERS")
    print("=" * 60)
    updated = 0
    not_found = []
    for fname, (fn, ln, email) in PROGRAM_MANAGERS.items():
        if not email:
            continue
        user = get_or_create_user(fn, ln, email, "program_manager")
        if not user:
            continue
        filieres = Filiere.objects.filter(name__iexact=fname, manager__isnull=True)
        count = filieres.count()
        if count == 0:
            already = Filiere.objects.filter(name__iexact=fname, manager__isnull=False).count()
            if already == 0:
                not_found.append(fname)
            continue
        filieres.update(manager=user)
        updated += count
        print(f"  → {fname}: {count} filiere(s) → manager={fn} {ln} (id={user.id})")
    print(f"\nSummary: {updated} filieres updated")
    if not_found:
        print(f"  Not matched (no filiere with that name in DB):")
        for nf in not_found:
            print(f"    - {nf}")
    # Handle filieres without official data
    still_null = Filiere.objects.filter(manager__isnull=True).exclude(name__iexact="Test Filiere").count()
    print(f"  Remaining NULL managers: {still_null}")


if __name__ == "__main__":
    assign_heads()
    assign_managers()

    print()
    print("=" * 60)
    print("FINAL STATE")
    print("=" * 60)
    for d in Department.objects.all():
        h = d.head
        h_name = f"{h.first_name} {h.last_name}" if h else "—"
        print(f"  {d.name}: head = {h_name}")
    print()
    for f in Filiere.objects.filter(manager__isnull=False).order_by("department_id", "name"):
        m = f.manager
        print(f"  {f.name} (dept={f.department_id}) → {m.first_name} {m.last_name}")
