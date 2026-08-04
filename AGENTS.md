
## Objective
- Un Ã©tudiant = un email unique ou un Code Massar unique dans la base. Pas de doublons.
- Un Ã©tudiant peut Ãªtre inscrit dans plusieurs modules, semestres et annÃ©es universitaires.
- RÃ©utilisation des fiches existantes, mise Ã  jour des inscriptions uniquement.
- Seuls les utilisateurs avec `role=department_head` peuvent Ãªtre chefs de dÃ©partement.
- Seuls les utilisateurs avec `role=program_manager` peuvent Ãªtre responsables de filiÃ¨re.
- Suppression de la passerelle enseignant â†’ chef de dÃ©partement / responsable filiÃ¨re.

## Key Details
- 5 user roles: admin, teacher, student, department_head, program_manager (dynamic field visibility)
- Server: 8000, admin: admin@umi.ac.ma / test1234
- Real DB: PostgreSQL (Neon)
- Student model: `email` (not unique), `code_massar` (unique=True), `classe` (FK â†’ Classe), `modules` (M2M via StudentModuleEnrollment)
- `Department.head` et `Filiere.manager` sont des ForeignKey vers User â€” validation du rÃ´le dans les serializers.
- Pas de migrations, pas de changement de schÃ©ma.

## Completed

### Student deduplication (serializer + import)
- **`StudentSerializer`** (`backend/users/serializers.py`):
  - `create()` lookup par **email** d'abord, puis **code_massar**; si trouvÃ©, met Ã  jour les champs et crÃ©e `StudentModuleEnrollment`
  - Conflit de code_massar â†’ `ValidationError`
  - `validate_code_massar()` allÃ©gÃ© (uniquement update, exclusion de soi)
  - `code_massar = serializers.CharField()` pour supprimer le `UniqueValidator` automatique de DRF
- **`_process_import_row()`** (`backend/users/services/student_import.py`):
  - Lookup email-first puis code_massar; mise Ã  jour du code_massar si trouvÃ© par email (avec vÃ©rification de conflit)
  - `_process_import_row` sauvegarde `code_massar` aprÃ¨s modification (`save(update_fields=["code_massar"])`)
- **Test `test_import_rejects_email_linked_to_other_student`** mis Ã  jour : email-match acceptÃ© + code_massar mis Ã  jour (au lieu du rejet)
- **7 tests d'import passent** : crÃ©ation, rÃ©utilisation email+massar, email+nouveau massar, massar+nouvel email, conflit massar, multiple modules, conflit email

### Restriction des rÃ´les department_head / program_manager
- **`DepartmentSerializer.validate_head()`** (`backend/curriculum/serializers.py`) : seul `role="department_head"` autorisÃ©; rejet si dÃ©jÃ  head d'un autre dÃ©partement
- **`FiliereSerializer.validate_manager_id()`** (`backend/curriculum/serializers.py`) : seul `role="program_manager"` autorisÃ©; rejet si dÃ©jÃ  manager d'une autre filiÃ¨re
- **`UserCreateSerializer`** et **`UserUpdateSerializer`** (`backend/users/serializers.py`) :
  - Suppression de `is_department_head`, `is_program_manager` (teacher_bridge)
  - `department.head` attribuÃ© uniquement si `role == "department_head"`
  - `filiere.manager` attribuÃ© uniquement si `role == "program_manager"`
  - Nettoyage automatique lors du changement de rÃ´le

### UI cleanup â€” checkbox suppression
- **`admin-departments.js`** : `loadDeptHeadSelect()` fetch `/users/?role=department_head` (plus teacher+admin)
- **`admin-departments.js`** : `manageFiliereManagers()` filtre sur `role === 'program_manager'` (plus teacher+program_manager+admin)
- **`admin-filieres.js`** : `loadUsersForManagerSelect()` fetch `/users/?role=program_manager` (plus teacher+admin)
- **`admin.html`** : retrait des champs `uIsAlsoTeacher`, `uIsDeptHead`, `euIsAlsoTeacher`, `euIsDeptHead` des modales add/edit user
- **`admin.html`** : retrait des Ã©couteurs d'Ã©vÃ©nement `uIsDeptHead`, `euIsDeptHead`
- **`admin.html`** : retrait du bloc `is_also_teacher`/`is_department_head` dans `buildPayload`
- **`admin-users.js`** : retrait de `euIsAlsoTeacher`, `euIsDeptHead`, `is_also_teacher`, `is_department_head` dans les blocs `openEditUser()` et `buildPayload()`
- **`admin_users.html`** : retrait des 4 champs `uIsAlsoTeacher`, `uIsDeptHead`, `euIsAlsoTeacher`, `euIsDeptHead`
- **`admin-teachers.js`** : `openEditTeacher()` ne rÃ©fÃ©rence plus `tIsDeptHead`/`etIsDeptHead` (utilise les modales `modalAddUser`/`modalEditUser`)
- **`admin_teachers.html`** : retrait des champs `tIsDeptHead`, `etIsDeptHead`
- **`buildPayload` (admin.html)** : retrait des blocs `is_also_teacher`, `is_department_head` pour le rÃ´le teacher

## Tested
- **7 tests d'import Ã©tudiant** : tous OK
- **9 tests d'import teacher** : Ã©checs prÃ©existants (`relation "departments" does not exist` dans la DB de test, non liÃ© aux changements)

## Feature: Rapport Excel mensuel â€” Charge horaire enseignants

### Endpoint
- `GET /api/v1/teacher-monthly-report/` â†’ `teacher_monthly_report` dans `backend/users/views.py`
- GÃ©nÃ¨re un fichier `.xlsx` avec openpyxl

### Filtres (query params)
- `department_id`, `semestre_id`, `filiere_id`, `teacher_id`
- `month` + `year` (ex: month=7, year=2026) **OU** `start_date` + `end_date`

### Calcul
- CM (Cours) = durÃ©e rÃ©elle (end_time - start_time)
- TD = durÃ©e Ã· 1,5
- TP = durÃ©e Ã· 1,5
- Seules les sÃ©ances actives (`is_active=True`) sont comptÃ©es

### Colonnes Excel
Enseignant, DÃ©partement, FiliÃ¨re, Nb sÃ©ances CM/TD/TP, Total heures CM/TD/TP, Charge horaire totale, Total sÃ©ances
- Ligne `TOTAL GÃ‰NÃ‰RAL` Ã  la fin
- En-tÃªtes en gras, colonnes ajustÃ©es automatiquement
- Nom fichier : `Charge_Horaire_Enseignants_MM_YYYY.xlsx`

### Permissions
- **admin** : tous les enseignants
- **department_head** : enseignants de son dÃ©partement (via `classe.department` ou `classe.filiere.department`)
- **program_manager** : enseignants de sa filiÃ¨re

### Frontend
- `/admin/workload/` â†’ `admin_workload.html` (extends `admin_base.html`)
- `admin-workload.js` : chargement en cascade (semestre â†’ filiÃ¨re, filtre par dÃ©partement), sÃ©lecteurs mois/annÃ©e ou intervalle de dates

## Known Bugs
- Missing teachers import template endpoint: `GET /teachers/import-excel/template/` returns 404.
- Standalone pages (`admin_teachers.html`, `admin_absences.html`, etc.) have broken template blocks (`page_title`, `modals`, `extra_js` not defined in `admin_base.html`).

## Relevant Files
- `backend/users/serializers.py` â€” StudentSerializer dedup, UserCreateSerializer/UserUpdateSerializer restriction rÃ´les
- `backend/users/services/student_import.py` â€” _process_import_row email-first lookup, code_massar save
- `backend/curriculum/serializers.py` â€” DepartmentSerializer.validate_head(), FiliereSerializer.validate_manager_id()
- `backend/templates/admin.html` â€” modales utilisateur (buildPayload, openEditUser, champs checkbox)
- `backend/templates/admin-users.js` â€” openEditUser(), buildPayload() cleanup
- `backend/templates/admin-departments.js` â€” loadDeptHeadSelect(), manageFiliereManagers() role filters
- `backend/templates/admin-filieres.js` â€” loadUsersForManagerSelect() role filter
- `backend/templates/admin_users.html` â€” champs checkbox add/edit
- `backend/templates/admin-teachers.js` â€” openEditTeacher() (utilise modales admin.html)
- `backend/templates/admin_teachers.html` â€” champs tIsDeptHead/etIsDeptHead (supprimÃ©s)
- `backend/users/tests_import.py` â€” test mis Ã  jour pour email-match+massar update

## Mobile (Flutter) : parité Enseignant / Étudiant — État
- Objectif : replicer le Web pour roles 	eacher et student uniquement (autres roles ? ole_not_supported_screen.dart). Backend/Web inchangés.
- mobile/lib — 0 erreur et 0 warning lutter analyze (seuls restent des infos withOpacity). lutter test OK. lutter build apk --debug OK.
- Roles routés depuis splash_screen.dart / login_screen.dart via _routeForRole.

### Enseignant (espaces complet)
- Dashboard (TeacherDashboardScreen) : carte bienvenue, grille stats globales (présents/absents/taux/étudiants), séances récentes, présences en direct + bouton refresh + tirer-pour-rafraichir.
- Sync auto : TeacherHomeScreen Timer 30 s -> efreshDashboardLive() sur onglets Accueil/Présences/Stats + refresh au retour foreground (WidgetsBindingObserver). Rechargement après action : SessionsScreen re-ouvre puis efreshSessions() (conserve classe sélectionnée).
- Séances : SessionsScreen (chips classes, liste, état temps réel), SessionFormScreen (création/edit ; vérif dispo via _available -> bannière lieux dispo), reload après retour.
- Détail séance (SessionDetailScreen) : 5 onglets – Présences, Carte(GPS), QR, Statistiques, Suspects. Bouton export feuille de présence XLSX dans l'AppBar.
- Export XLSX : DioClient.downloadBytes() (ResponseType.bytes) + TeacherService.exportSessionXlsx(sessionId) (GET /attendance/session/\{id\}/export/) + FileShareService.shareXlsx() (share_plus). Endpoints ajoutés : sessionExportEndpoint, sessionReportEndpoint.
- Carte GPS : _MapTab (flutter_map + latlong2) affiche les marqueurs des présences (champs latitude/longitude ajoutés à AttendanceModel + SessionAttendance, parsés depuis ttendance_status/latitude/longitude du serializer).
- QR : onglet QR (current-qr), GenerateQrScreen (expiration, rayon, GPS), closeSession.
- Stats globales : TeacherStatisticsScreen périodes 7/30/90 — fix : loadGlobalStats(period) recharge au changement de période.
- Live attendance : TeacherAttendanceScreen (liste scans récents) + sync 30 s.

### Étudiant
- StudentHomeScreen 4 onglets (Accueil HomeScreen scan/validation, Emploi du temps, Stats, Profil). Historique : StudentProvider.loadHistory (/attendance/my/). Stats : taux présent calculé via ttendanceStatus != 'absent' (champ ttendance_status ajouté à AttendanceModel). StudentProfileScreen, StudentScheduleScreen (Cours/Présences).

### Notes / limites
- Pas de DELDT sšance côté Web enseignant : non répliqu‚ (le backend l'expose, mais pas d'UI Web de reference).
- Live temps réel par polling HTTP 30 s (pas de WebSocket mobil en debut) ; le Web utilise ws /ws/attendance/... — amélioration future possible.
