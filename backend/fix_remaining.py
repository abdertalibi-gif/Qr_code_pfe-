"""Fix remaining filieres without department_id"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()
from curriculum.models import Filiere
from users.models import Department

import unicodedata
def normalize(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').lower()

departments = {}
for d in Department.objects.all():
    key = normalize(d.name)
    departments[key] = d.id
    print("  Dept: '%s' -> normalized '%s' -> id=%d" % (d.name, key, d.id))

for f in Filiere.objects.filter(name="Mathematiques et Applications", department__isnull=True):
    f.department_id = departments.get("mathematiques")
    f.save(update_fields=["department_id"])
    print("  Updated filiere %d (%s)" % (f.id, f.name))

for prefix in ["Geodynamique", "Geosciences", "Hydrologie"]:
    for f in Filiere.objects.filter(name__startswith=prefix, department__isnull=True):
        f.department_id = departments.get("geologie")
        f.save(update_fields=["department_id"])
        print("  Updated filiere %d (%s)" % (f.id, f.name))

null = Filiere.objects.filter(department__isnull=True)
print("\nRemaining without department:", null.count())
for f in null:
    print("  id=%d name=%s" % (f.id, f.name))
