import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.db import connection, reset_queries
from django.conf import settings
from rest_framework.test import APIClient
from users.models import User
from courses.models import Session

settings.DEBUG = True
client = APIClient()

admin_user = User.objects.filter(role="admin", is_active=True).first()
assert admin_user is not None, "Admin user must exist"
client.force_authenticate(user=admin_user)

print("=" * 70)
print("VERIFICATION END-TO-END DE L'API /api/v1/sessions/")
print("=" * 70)

# 1. Requête principale admin (toutes les séances)
reset_queries()
t0 = time.time()
res = client.get("/api/v1/sessions/")
dur = time.time() - t0
queries_count = len(connection.queries)

print(f"\n1. GET /api/v1/sessions/ (Admin)")
print(f"   Status Code: {res.status_code}")
print(f"   Response time: {dur:.3f} s")
print(f"   SQL Queries fired: {queries_count}")

assert res.status_code == 200, f"Expected 200, got {res.status_code}"
results = res.data.get("results", []) if isinstance(res.data, dict) else res.data
print(f"   Total sessions count in response: {res.data.get('count', len(results))}")
print(f"   Sessions returned in page: {len(results)}")

# Vérifier qu'il y a bien des données existantes
assert len(results) > 0, "Doit renvoyer les séances réelles de la base"
first = results[0]
print(f"   Exemple de séance chargée :")
print(f"     ID: {first.get('id')}")
print(f"     Title: {first.get('title')}")
print(f"     Subject: {first.get('subject')}")
print(f"     Class name: {first.get('class_name')} / {first.get('classe_name')}")
print(f"     Matiere name: {first.get('matiere_name')} / {first.get('module_name')}")
print(f"     Teacher name: {first.get('teacher_name')}")
print(f"     Room name: {first.get('room_name')}")
print(f"     Status: {first.get('status')}")

# Vérifier les champs requis
required_keys = ["id", "title", "subject", "class_name", "classe_name", "matiere_name", "teacher_name", "status"]
for k in required_keys:
    assert k in first, f"Missing key {k} in serialized session"

# 2. Test avec filtre par classe
first_classe_id = first.get("classe")
if first_classe_id:
    reset_queries()
    t0 = time.time()
    res_classe = client.get(f"/api/v1/sessions/?classe={first_classe_id}")
    dur_classe = time.time() - t0
    results_classe = res_classe.data.get("results", []) if isinstance(res_classe.data, dict) else res_classe.data
    print(f"\n2. GET /api/v1/sessions/?classe={first_classe_id} (Filtre classe)")
    print(f"   Status Code: {res_classe.status_code} ({dur_classe:.3f}s, {len(connection.queries)} queries)")
    print(f"   Filtered count: {len(results_classe)}")
    assert res_classe.status_code == 200
    for s in results_classe:
        assert s["classe"] == first_classe_id

# 3. Test avec filtre par enseignant
first_teacher_id = first.get("teacher")
if first_teacher_id:
    reset_queries()
    t0 = time.time()
    res_teacher = client.get(f"/api/v1/sessions/?teacher={first_teacher_id}")
    dur_teacher = time.time() - t0
    results_teacher = res_teacher.data.get("results", []) if isinstance(res_teacher.data, dict) else res_teacher.data
    print(f"\n3. GET /api/v1/sessions/?teacher={first_teacher_id} (Filtre enseignant)")
    print(f"   Status Code: {res_teacher.status_code} ({dur_teacher:.3f}s, {len(connection.queries)} queries)")
    print(f"   Filtered count: {len(results_teacher)}")
    assert res_teacher.status_code == 200
    for s in results_teacher:
        assert s["teacher"] == first_teacher_id

# 4. Test pour enseignant connecté (role teacher)
teacher_user = User.objects.filter(role="teacher", is_active=True).first()
if teacher_user:
    t_client = APIClient()
    t_client.force_authenticate(user=teacher_user)
    reset_queries()
    t0 = time.time()
    res_t = t_client.get("/api/v1/sessions/")
    dur_t = time.time() - t0
    results_t = res_t.data.get("results", []) if isinstance(res_t.data, dict) else res_t.data
    print(f"\n4. GET /api/v1/sessions/ (Enseignant: {teacher_user.email})")
    print(f"   Status Code: {res_t.status_code} ({dur_t:.3f}s, {len(connection.queries)} queries)")
    print(f"   Sessions count: {len(results_t)}")
    assert res_t.status_code == 200

print("\n" + "=" * 70)
print("TOUS LES TESTS END-TO-END ONT REUSSI AVEC SUCCES !")
print("=" * 70)
