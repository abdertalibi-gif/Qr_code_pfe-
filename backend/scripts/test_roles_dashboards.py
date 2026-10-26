import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.test import Client
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def log(msg):
    try:
        print(msg, flush=True)
    except Exception:
        print(msg.encode('ascii', 'replace').decode('ascii'), flush=True)

log("=" * 80)
log("AUDIT DÉTAILLÉ DES DASHBOARDS PAR RÔLE")
log("=" * 80)

# ─── 1. ROUTAGE DES PAGES HTML ──────────────────────────────────────────────
log("\n[1/3] VÉRIFICATION DU CHARGEMENT DES TEMPLATES HTML (SERVEUR WEB)")
html_client = Client()

dashboard_routes = [
    ("/", "Landing Page"),
    ("/login/", "Page de connexion"),
    ("/admin-ui/", "Dashboard Administrateur"),
    ("/teacher/", "Dashboard Enseignant"),
    ("/student/", "Dashboard Étudiant"),
    ("/attend/", "Page Scan QR Étudiant"),
    ("/admin/attendance-live/", "Sous-page Admin: Présence Live"),
    ("/admin/users/", "Sous-page Admin: Utilisateurs"),
    ("/admin/teachers/", "Sous-page Admin: Enseignants"),
    ("/admin/students/", "Sous-page Admin: Étudiants"),
    ("/admin/classes/", "Sous-page Admin: Classes"),
    ("/admin/curriculum/", "Sous-page Admin: Curriculum"),
    ("/admin/sessions/", "Sous-page Admin: Séances"),
    ("/admin/departments/", "Sous-page Admin: Départements"),
    ("/admin/filieres/", "Sous-page Admin: Filières"),
    ("/admin/rooms/", "Sous-page Admin: Salles"),
    ("/admin/reports/", "Sous-page Admin: Rapports"),
    ("/admin/statistics/", "Sous-page Admin: Statistiques"),
    ("/admin/settings/", "Sous-page Admin: Paramètres"),
    ("/admin/attendances/", "Sous-page Admin: Présences"),
    ("/admin/absences/", "Sous-page Admin: Absences"),
    ("/admin/workload/", "Sous-page Admin: Charge de travail"),
]

for route, label in dashboard_routes:
    t0 = time.time()
    resp = html_client.get(route)
    dt = (time.time() - t0) * 1000
    if resp.status_code == 200:
        log(f"  [OK 200] {route:<28} | {label} ({dt:.0f}ms)")
    else:
        log(f"  [ERREUR {resp.status_code}] {route:<28} | {label}")

# ─── 2. VÉRIFICATION DES COMPTES PAR RÔLE ────────────────────────────────────
log("\n[2/3] VÉRIFICATION DE LA DISPONIBILITÉ DES RÔLES EN BASE DE DONNÉES")
roles = ["admin", "teacher", "student", "department_head", "program_manager"]
active_users = {}

for role in roles:
    u = User.objects.filter(role=role, is_active=True).first()
    if u:
        active_users[role] = u
        log(f"  [ROLE: {role:<16}] {u.email} (ID={u.id}, Nom={u.first_name} {u.last_name})")
    else:
        log(f"  [ROLE: {role:<16}] AUCUN COMPTE ACTIF EN BASE !")

# ─── 3. VÉRIFICATION FONCTIONNELLE DU DASHBOARD DE CHAQUE RÔLE ──────────────
log("\n[3/3] TEST DES ENDPOINTS DE DASHBOARD SPÉCIFIQUES À CHAQUE RÔLE")
api_client = APIClient()

# Définition des endpoints réels appelés par le dashboard de chaque rôle
role_dashboards = {
    "admin": {
        "label": "Tableau de bord Administrateur (/admin-ui/)",
        "endpoints": [
            ("GET", "/api/v1/dashboard/counts/", "Compteurs d'en-tête (stats rapides)"),
            ("GET", "/api/v1/statistics/", "Statistiques globales de présence"),
            ("GET", "/api/v1/absence-stats/", "Statistiques d'absence et alertes"),
            ("GET", "/api/v1/users/", "Liste complète des utilisateurs"),
            ("GET", "/api/v1/teachers/", "Gestion des enseignants"),
            ("GET", "/api/v1/students/", "Gestion des étudiants"),
            ("GET", "/api/v1/classes/", "Gestion des classes"),
            ("GET", "/api/v1/sessions/", "Gestion des séances"),
            ("GET", "/api/v1/departments/", "Gestion des départements"),
            ("GET", "/api/v1/rooms/", "Gestion des salles et amphis"),
            ("GET", "/api/v1/blocks/", "Gestion des blocs"),
            ("GET", "/api/v1/curriculum/filieres/", "Curriculum: Filières"),
            ("GET", "/api/v1/curriculum/modules/", "Curriculum: Modules"),
            ("GET", "/api/v1/teacher-workload/", "Charge horaire enseignants"),
            ("GET", "/api/v1/settings/", "Paramètres système"),
            ("GET", "/api/v1/attendance/", "Journal des présences"),
        ]
    },
    "teacher": {
        "label": "Tableau de bord Enseignant (/teacher/)",
        "endpoints": [
            ("GET", "/api/v1/auth/me/", "Profil enseignant connecté"),
            ("GET", "/api/v1/classes/", "Mes classes assignées"),
            ("GET", "/api/v1/sessions/", "Mes séances de cours"),
            ("GET", "/api/v1/attendance/", "Présences en direct de mes séances"),
            ("GET", "/api/v1/curriculum/modules/", "Modules enseignés"),
            ("GET", "/api/v1/blocks/", "Salles et blocs disponibles pour séance"),
        ]
    },
    "student": {
        "label": "Tableau de bord Étudiant (/student/)",
        "endpoints": [
            ("GET", "/api/v1/attendance/student/profile/", "Profil de l'étudiant et classe"),
            ("GET", "/api/v1/attendance/student/schedule/", "Emploi du temps des séances"),
            ("GET", "/api/v1/attendance/student/history/", "Historique personnel des présences"),
        ]
    },
    "department_head": {
        "label": "Tableau de bord Chef de Département (/admin-ui/ filtré)",
        "endpoints": [
            ("GET", "/api/v1/auth/me/", "Profil chef de département"),
            ("GET", "/api/v1/dashboard/counts/", "Compteurs filtrés par département"),
            ("GET", "/api/v1/classes/", "Classes de mon département"),
            ("GET", "/api/v1/sessions/", "Séances des filières de mon département"),
            ("GET", "/api/v1/curriculum/filieres/", "Filières de mon département"),
            ("GET", "/api/v1/absence-stats/", "Stats absences département"),
        ]
    },
    "program_manager": {
        "label": "Tableau de bord Responsable de Filière (/admin-ui/ filtré)",
        "endpoints": [
            ("GET", "/api/v1/auth/me/", "Profil responsable de filière"),
            ("GET", "/api/v1/classes/", "Classes de ma filière"),
            ("GET", "/api/v1/sessions/", "Séances de ma filière"),
            ("GET", "/api/v1/curriculum/modules/", "Modules de ma filière"),
            ("GET", "/api/v1/absence-stats/", "Stats absences de la filière"),
        ]
    }
}

for role, conf in role_dashboards.items():
    user = active_users.get(role)
    log("\n" + "-" * 70)
    log(f"ROLE : {role.upper()} - {conf['label']}")
    if not user:
        log("  [IGNORÉ] Aucun compte actif pour ce rôle.")
        continue
    log(f"  Utilisateur de test: {user.email}")
    api_client.force_authenticate(user=user)
    
    success_count = 0
    fail_count = 0
    
    for method, endpoint, desc in conf["endpoints"]:
        t0 = time.time()
        try:
            if method == "GET":
                res = api_client.get(endpoint)
            else:
                res = api_client.post(endpoint)
            dt = (time.time() - t0) * 1000
            
            if res.status_code == 200:
                count_str = ""
                if isinstance(res.data, list):
                    count_str = f"({len(res.data)} items)"
                elif isinstance(res.data, dict) and "results" in res.data:
                    count_str = f"({len(res.data['results'])} items, total={res.data.get('count')})"
                log(f"    ✓ OK 200 ({dt:>4.0f}ms) | {endpoint:<38} | {desc} {count_str}")
                success_count += 1
            elif res.status_code == 403:
                log(f"    ✕ 403 FORBIDDEN   | {endpoint:<38} | {desc}")
                fail_count += 1
            elif res.status_code == 404:
                log(f"    ✕ 404 NOT FOUND   | {endpoint:<38} | {desc}")
                fail_count += 1
            elif res.status_code >= 500:
                log(f"    ✕ {res.status_code} SERVER ERR | {endpoint:<38} | {desc} -> {str(res.data)[:100]}")
                fail_count += 1
            else:
                log(f"    ? {res.status_code} ({dt:>4.0f}ms) | {endpoint:<38} | {desc}")
        except Exception as e:
            log(f"    ✕ EXCEPTION      | {endpoint:<38} | {desc} -> {e}")
            fail_count += 1
            
    log(f"  Bilan {role.upper()} : {success_count} réussis, {fail_count} échecs.")

log("\n" + "=" * 80)
log("FIN DE L'AUDIT DES DASHBOARDS PAR RÔLE")
log("=" * 80)
