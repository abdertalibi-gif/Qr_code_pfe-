"""
Populate department_id for filieres based on official FS-UMI department mapping.
Run with: python populate_dept_data.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_mKh5b0YwsrZJ@ep-proud-hall-ap5q3y9d-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()

from curriculum.models import Filiere
from users.models import Department

# Department name -> id mapping (from existing DB data)
dept_map = {
    "Mathématiques":  1,
    "Informatique":   2,
    "Physique":       3,
    "Chimie":         4,
    "Biologie":       5,
    "Géologie":       6,
}

# Filiere name patterns -> department name
FILIERE_DEPT_MAP = {
    "Informatique": [
        "Genie Informatique",
        "Génie Informatique",
        "Digitalisation",
        "Sciences des Donnees et Intelligence Artificielle",
        "Sciences des données et Intelligence Artificielle",
        "Intelligence Artificielle et Systemes de Decisions Optimales",
        "Intelligence Artificielle et Systèmes de Décisions Optimales",
        "Intelligence Artificielle et Recherche Operationnelle",
        "Intelligence Artificielle et Recherche Opérationnelle",
        "Intelligence et Securite des Objets Connectes",
        "Intelligence et Sécurité des Objets Connectés",
        "Systemes Intelligents et Recherche Operationnelle",
        "Systèmes Intelligents et Recherche Opérationnelle",
    ],
    "Mathématiques": [
        "Mathematiques et Applications",
        "Mathématiques et Applications",
    ],
    "Chimie": [
        "Chimie Organique et Bioorganique",
        "Chimie Physique Appliquee et Environnement",
        "Chimie Physique Appliquée et Environnement",
        "Chimie des Materiaux et des Procedes Industriels",
        "Chimie des Matériaux et des Procédés Industriels",
    ],
    "Physique": [
        "Physique Appliquee et Ingenierie Physique",
        "Physique Appliquée et Ingénierie Physique",
        "Mecanique des Fluides et Energetique",
        "Mécanique des Fluides et Énergétique",
        "Electronique et Systemes",
        "Électronique et Systèmes",
        "Plasturgie et Ingenierie Biomedicale",
        "Plasturgie et Ingénierie Biomédicale",
        "Materiaux et Energetique",
        "Matériaux et Énergétique",
    ],
    "Biologie": [
        "Biologie Cellulaire et Physiologie Humaine",
        "BioActifs, Sante et Environnement",
        "BioActifs, Santé et Environnement",
    ],
    "Géologie": [
        "Geosciences et Geologie de l'Ingenieur",
        "Géosciences et Géologie de l'Ingénieur",
        "Hydrologie et Hydrogeologie",
        "Hydrologie et Hydrogéologie",
        "Geodynamique et Georessources",
        "Géodynamique et Géoressources",
    ],
}

updated = 0
skipped = 0
not_found = []

for dept_name, filiere_names in FILIERE_DEPT_MAP.items():
    dept_id = dept_map.get(dept_name)
    if not dept_id:
        print(f"ERROR: Department '{dept_name}' not found in dept_map")
        continue
    
    for fname in filiere_names:
        filieres = Filiere.objects.filter(name__iexact=fname, department__isnull=True)
        count = filieres.count()
        if count == 0:
            filieres_with_dept = Filiere.objects.filter(name__iexact=fname, department__isnull=False)
            if filieres_with_dept.count() > 0:
                skipped += filieres_with_dept.count()
            else:
                not_found.append(fname)
            continue
        
        updated += count
        filieres.update(department_id=dept_id)
        print(f"  → {fname}: {count} filiere(s) → {dept_name} (dept_id={dept_id})")

print(f"\nSummary:")
print(f"  Updated: {updated} filieres")
print(f"  Skipped (already assigned): {skipped}")
print(f"  Not found: {len(not_found)}")
for nf in not_found:
    print(f"    - {nf}")

# Also check if 'Test Filiere' was affected
test_f = Filiere.objects.filter(name__iexact="Test Filiere").first()
if test_f:
    print(f"\n'Test Filiere': id={test_f.id}, department_id={test_f.department_id}")
