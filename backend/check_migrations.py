import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Configuration lue depuis l'environnement / .env : aucun identifiant en dur.
# load_dotenv n'ecrase pas une variable DATABASE_URL deja definie.
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT app, name, applied FROM django_migrations ORDER BY app, name")
    rows = cursor.fetchall()
    print("Applied migrations:")
    for r in rows:
        print(f"  {r[0]:20s} {r[1]:50s} {r[2]}")

    # Check existing roles in users table
    cursor.execute("SELECT DISTINCT role FROM users ORDER BY role")
    roles = [r[0] for r in cursor.fetchall()]
    print(f"\nExisting roles in users table: {roles}")

    # Check existing departments
    cursor.execute("SELECT id, name, head_id FROM departments")
    depts = cursor.fetchall()
    print(f"\nExisting departments ({len(depts)}):")
    for d in depts:
        print(f"  id={d[0]} name={d[1]} head_id={d[2]}")

    # Check existing filieres with department_id and manager_id
    cursor.execute("SELECT id, name, department_id, manager_id FROM filieres")
    fils = cursor.fetchall()
    print(f"\nExisting filieres ({len(fils)}):")
    for f in fils:
        print(f"  id={f[0]} name={f[1]} dept_id={f[2]} mgr_id={f[3]}")

    # Check existing faculties
    cursor.execute("SELECT id, name, code FROM faculties")
    facs = cursor.fetchall()
    print(f"\nExisting faculties ({len(facs)}):")
    for f in facs:
        print(f"  id={f[0]} name={f[1]} code={f[2]}")

    # Check academic_years
    cursor.execute("SELECT id, label, is_current FROM academic_years")
    yrs = cursor.fetchall()
    print(f"\nExisting academic_years ({len(yrs)}):")
    for y in yrs:
        print(f"  id={y[0]} label={y[1]} is_current={y[2]}")
