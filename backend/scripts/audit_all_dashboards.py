import os
import sys
import re
import glob

sys.path.insert(0, os.path.abspath("backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.test import Client
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("AUDIT DE TOUS LES DASHBOARDS ET RÔLES")
print("=" * 80)

# 1. Vérification des templates HTML et ressources statiques
templates_dir = os.path.join("backend", "templates")
html_files = sorted(glob.glob(os.path.join(templates_dir, "*.html")))

print("\n--- 1. AUDIT DES FICHIERS TEMPLATES HTML ---")
client = Client()

for hfile in html_files:
    fname = os.path.basename(hfile)
    with open(hfile, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE)
    links = re.findall(r'<link[^>]*href=[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE)
    
    missing = []
    for s in scripts:
        if s.startswith(("http://", "https://", "//")):
            continue
        rel = s.lstrip("/")
        t_path = os.path.join(templates_dir, rel)
        s_path = os.path.join("backend", "static", rel)
        if not os.path.exists(t_path) and not os.path.exists(s_path):
            missing.append(f"JS: {s}")
            
    for l in links:
        if l.startswith(("http://", "https://", "//")):
            continue
        rel = l.lstrip("/")
        t_path = os.path.join(templates_dir, rel)
        s_path = os.path.join("backend", "static", rel)
        if not os.path.exists(t_path) and not os.path.exists(s_path):
            missing.append(f"CSS: {l}")
            
    # Check if template is served by a URL
    routes = {
        "admin.html": "/admin-ui/",
        "admin_attendance_live.html": "/admin/attendance-live/",
        "admin_users.html": "/admin/users/",
        "admin_teachers.html": "/admin/teachers/",
        "admin_students.html": "/admin/students/",
        "admin_classes.html": "/admin/classes/",
        "admin_curriculum.html": "/admin/curriculum/",
        "admin_sessions.html": "/admin/sessions/",
        "admin_departments.html": "/admin/departments/",
        "admin_filieres.html": "/admin/filieres/",
        "admin_rooms.html": "/admin/rooms/",
        "admin_reports.html": "/admin/reports/",
        "admin_statistics.html": "/admin/statistics/",
        "admin_settings.html": "/admin/settings/",
        "admin_attendances.html": "/admin/attendances/",
        "admin_absences.html": "/admin/absences/",
        "admin_assistants.html": "/admin/assistants/",
        "admin_workload.html": "/admin/workload/",
        "teacher.html": "/teacher/",
        "student.html": "/student/",
        "attend.html": "/attend/",
        "landing.html": "/",
        "login.html": "/login/",
        "password_reset.html": None,
    }
    
    route = routes.get(fname)
    status_str = "NON ROUTÉ"
    if route:
        resp = client.get(route)
        status_str = f"GET {route} -> {resp.status_code}"
        
    print(f"{fname:<30} | {status_str:<25} | Scripts: {len(scripts):<2} | CSS: {len(links):<2} | Manquants: {missing or 'Aucun'}")

# 2. Vérification des utilisateurs par rôle
print("\n--- 2. VÉRIFICATION DES UTILISATEURS PAR RÔLE ---")
roles = ["admin", "teacher", "student", "department_head", "program_manager"]
users_by_role = {}
for r in roles:
    u = User.objects.filter(role=r, is_active=True).first()
    users_by_role[r] = u
    if u:
        print(f"Rôle [{r}]: Trouvé -> ID={u.id}, Email={u.email}, Nom={u.first_name} {u.last_name}")
    else:
        print(f"Rôle [{r}]: AUCUN UTILISATEUR ACTIF TROUVÉ !")

# 3. Test des dashboards et endpoints clés par rôle
print("\n--- 3. TEST D'ACCÈS AUX DASHBOARDS ET ENDPOINTS PAR RÔLE ---")
api_client = APIClient()

endpoints_to_test = [
    # General / Admin endpoints
    ("GET", "/api/v1/dashboard/counts/"),
    ("GET", "/api/v1/statistics/"),
    ("GET", "/api/v1/absence-stats/"),
    ("GET", "/api/v1/users/"),
    ("GET", "/api/v1/teachers/"),
    ("GET", "/api/v1/students/"),
    ("GET", "/api/v1/classes/"),
    ("GET", "/api/v1/sessions/"),
    ("GET", "/api/v1/filieres/"),
    ("GET", "/api/v1/departments/"),
    ("GET", "/api/v1/rooms/"),
    ("GET", "/api/v1/blocks/"),
    ("GET", "/api/v1/amphitheaters/"),
    ("GET", "/api/v1/teacher-workload/"),
    ("GET", "/api/v1/settings/"),
    ("GET", "/api/v1/system-info/"),
    # Attendance endpoints
    ("GET", "/api/v1/attendance/"),
    ("GET", "/api/v1/attendance/records/"),
    ("GET", "/api/v1/attendance/sessions/"),
    ("GET", "/api/v1/attendance/reports/"),
    # Student specific
    ("GET", "/api/v1/attendance/student/profile/"),
    ("GET", "/api/v1/attendance/student/schedule/"),
    ("GET", "/api/v1/attendance/student/history/"),
]

for r, u in users_by_role.items():
    if not u:
        print(f"\n[RÔLE: {r.upper()}] Impossible de tester (aucun compte).")
        continue
    
    print(f"\n==========================================")
    print(f"TESTS POUR LE RÔLE : {r.upper()} ({u.email})")
    print(f"==========================================")
    api_client.force_authenticate(user=u)
    
    for method, ep in endpoints_to_test:
        try:
            if method == "GET":
                res = api_client.get(ep)
            else:
                res = api_client.post(ep)
            
            status = res.status_code
            detail = ""
            if status == 200:
                if isinstance(res.data, list):
                    detail = f"OK ({len(res.data)} items)"
                elif isinstance(res.data, dict):
                    if "results" in res.data and isinstance(res.data["results"], list):
                        detail = f"OK ({len(res.data['results'])} items / total={res.data.get('count', '?')})"
                    else:
                        detail = f"OK (dict keys: {list(res.data.keys())[:5]})"
            elif status == 403:
                detail = "403 FORBIDDEN (Accès restreint par permission)"
            elif status == 404:
                detail = "404 NOT FOUND (Endpoint introuvable)"
            elif status == 500:
                detail = f"500 SERVER ERROR: {res.data}"
            else:
                detail = f"{status}: {str(res.data)[:80]}"
                
            print(f"  {ep:<45} -> {status} | {detail}")
        except Exception as e:
            print(f"  {ep:<45} -> EXCEPTION: {e}")

print("\n--- FIN DU RAPPORT D'AUDIT DES DASHBOARDS ---")
