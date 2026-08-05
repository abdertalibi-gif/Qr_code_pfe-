
## Objective
- Un étudiant = un email unique ou un Code Massar unique dans la base. Pas de doublons.
- Un étudiant peut être inscrit dans plusieurs modules, semestres et années universitaires.
- Réutilisation des fiches existantes, mise à jour des inscriptions uniquement.
- Seuls les utilisateurs avec `role=department_head` peuvent être chefs de département.
- Seuls les utilisateurs avec `role=program_manager` peuvent être responsables de filière.
- Suppression de la passerelle enseignant → chef de département / responsable filière.
- **Isolation enseignant** : un enseignant ne voit QUE les classes explicitement affectées par l'admin (`assigned_classes`). Jamais de classes de collègues, jamais de classes « de tout le département ». Retrait/ajout d'affectation → visible immédiatement. Nouvel enseignant = 0 classe.

## Key Details
- 5 user roles: admin, teacher, student, department_head, program_manager (dynamic field visibility)
- Server: 8000, admin: admin@umi.ac.ma / test1234
- Real DB: PostgreSQL (Neon)
- Student model: `email` (not unique), `code_massar` (unique=True), `classe` (FK → Classe), `modules` (M2M via StudentModuleEnrollment)
- `Department.head` et `Filiere.manager` sont des ForeignKey vers User — validation du rôle dans les serializers.
- Pas de migrations, pas de changement de schéma.
- `User.assigned_classes` (M2M → Classe, related_name=`teachers`) = source de vérité de l'isolation enseignant (Web + Mobile + Backend).
- **Ne jamais auto-affecter des classes à un enseignant** (ni toutes celles du département, ni à l'import, ni à la création). Seule source : `assigned_class_ids` envoyé par l'admin.
- Les séances créées ajoutent leur classe à `assigned_classes` du teacher (`courses/views.py:79-81`) — mécanisme voulu : un enseignant gère les classes de ses séances.

## Completed

### Isolation enseignant — classes assignées (Web + Mobile + Backend)
- **`UserCreateSerializer.create`** / **`UserUpdateSerializer.update`** (`backend/users/serializers.py`) : suppression de l'auto-affectation de TOUTES les classes du département (`Classe.objects.filter(Q(department=...) | Q(filiere__department=...))`). Seules les classes explicitement fournies via `assigned_class_ids` sont assignées. Update sans `assigned_class_ids` → classes inchangées (PATCH partiel sûr).
- **`teacher_import.py`** (`backend/users/services/teacher_import.py`) : suppression du bloc « Assign department classes to all imported users » (les enseignants importés n'ont plus aucune classe par défaut) + nettoyage imports/variables morts (`Q`, `Classe`, `user_dept_map`).
- **`ClasseViewSet.get_queryset`** (`backend/users/views.py`) : teacher → `filter(teachers=user)` uniquement (plus `| Q(sessions__teacher=user)`). Classe retirée → disparaît immédiatement.
- **`StudentViewSet.get_queryset`** : teacher → `filter(classe__teachers=user)` uniquement (plus `| Q(classe__sessions__teacher=user)`).
- **`SessionSerializer.validate`** (`backend/courses/serializers.py`) : fallback `has_sessions` supprimé — un enseignant ne peut créer/modifier une séance QUE dans une classe affectée (« Vous n'êtes pas affecté à cette classe. »).
- **UI admin** (`backend/templates/admin.html`) : selects « Classes assignées » (`uClasses`/`euClasses`) maintenant visibles pour le rôle **teacher** (`data-roles="teacher,department_head,program_manager"`). `buildPayload` envoyait déjà `assigned_class_ids` pour teacher.
- **i18n** : `noClasses` → « Aucune classe ne vous est affectée. » (état vide teacher.html déjà branché dessus).
- Vérifié scopé pour teacher (déjà OK, non modifié) : `SessionViewSet` (`teacher=user`), `AllAttendanceListView`/`SessionAttendanceListView` (`session__teacher=user` + `teacher_can_manage`), `teacher_can_manage` (`courses/models.py:170-177`), `teacher_list` (`[]`), `ExportWizardService` (`session__teacher=user`), `admin_statistics` (branche teacher 879-884), `teacher_workload`/`teacher_monthly_report` (403 pour teacher — admin/dept_head/program_manager uniquement).
- **Mobile** : aucune modif nécessaire — `TeacherService.fetchClasses()` → `/classes/` (backend scopé), état vide « Aucune classe assignée » déjà présent (`sessions_screen.dart`).
- Validation : `django check` OK, `compileall` OK, `node --check` OK. Tests backend bloqués (DB test Neon verrouillée, problème préexistant).

### Séances créées UNIQUEMENT par les enseignants (2026-08-05)
- **Nouvelle permission `IsTeacher`** (`backend/users/permissions.py`) : `role == "teacher"`.
- **`SessionViewSet.get_permissions()`** (`backend/courses/views.py`) : actions d'écriture `create`, `update`, `partial_update`, `destroy` **+ `generate_qr` + `close`** → `[IsAuthenticated(), IsTeacher()]` (403 pour admin, department_head, program_manager). Lecture (`list`, `retrieve`, `current_qr`, `available-*`) inchangée : admin/dept_head/program_manager peuvent toujours consulter/exporter.
- **`perform_create` simplifié** : branches department_head/program_manager supprimées (code mort), imports `IsAdmin`, `get_user_department`, `get_user_filiere_ids` nettoyés.
- **UI admin (`admin.html`)** : bouton « + Nouvelle séance » supprimé, colonne « Actions » (Supprimer) retirée du tableau des séances, `deleteSession()`, listener `btnOpenAddSession`, `SessionForm.init(...)` et `<script src="/session-form.js">` retirés.
- **`admin_sessions.html`** : bouton « + Nouvelle séance » et script session-form.js retirés ; tableau sans colonne Actions.
- **`admin-sessions.js`** : `openEditSession`/`deleteSession`/listener d'ajout supprimés (reste : liste, recherche, actualiser, export Excel).
- `session-form.js` ne reste chargé que par `teacher.html` (création de séance côté enseignant).
- **Workflow** : admin crée la classe → admin affecte l'enseignant (`assigned_class_ids`) → classe visible dans le dashboard de l'enseignant → l'enseignant crée ses séances (la classe est ajoutée automatiquement à `assigned_classes` à la création de séance) → les étudiants voient les séances via `/attendance/my-schedule/` et scannent le QR.
- Vérifié en direct : admin POST/PATCH/DELETE/generate-qr/close sur `/sessions/` → **403** ; teacher POST → 201 ; dept_head POST → 403 ; lecture admin → OK.

### Lieu par défaut de la classe (2026-08-05)
- **Déjà en place** : `Classe` a `location_type` (BLOC/AMPHI/BOTH_ALLOWED), `block`, `room`, `amphitheater` (`backend/users/models.py:261-290`), exposés par `ClasseSerializer` (`location_type`, `block_id`, `room_id`, `amphitheater_id`). Le formulaire admin (`admin-classes.js` → `clLocationType`/`clBlock`/`clRoom`/`clAmphi`) définit déjà ce lieu à la création de la classe.
- **`SessionSerializer.validate`** (`backend/courses/serializers.py`) : si une séance est créée **sans lieu** avec une classe ayant un lieu par défaut → auto-remplissage (`BLOC`/`BOTH_ALLOWED`+block+room → block ; `AMPHI`/`BOTH_ALLOWED`+amphi → amphitheater). **Création uniquement** (`not self.instance`) : un PATCH sans champs lieu préserve le lieu existant (changement exceptionnel conservé). Le conflit de salle reste vérifié ensuite.
- **Web `session_form.js`** : nouvelle méthode `_applyClassLocation(cls)` branchée dans `_preselectClass` (couvre sélection manuelle, auto-sélection si 1 seule classe, `SessionForm.open(classeId)`, édition — sautée en édition car le lieu de la séance est appliqué séparément). Au changement de classe → type de lieu + bloc + salle (ou amphi) préremplis, puis vérification de disponibilité (`_fetchAvailableLocations`) : si le lieu de la classe est occupé sur le créneau, la sélection est vidée et l'enseignant choisit un autre lieu. Hint ajouté sous le select « Type de lieu » (« Lieu par défaut de la classe, modifiable en cas de changement exceptionnel. »).
- **Mobile** : `ClasseModel` enrichi (`locationType`, `blockId`, `roomId`, `amphitheaterId` — `classe_model.dart`) ; `SessionFormScreen._applyClasseLocation()` applique le lieu de la classe à la sélection/auto-sélection (création uniquement, édition préservée) + `_fetchAvailability()`.
- Vérifié en direct : POST enseignant sans lieu → 201 avec `location_type=block, block=9, room=67` (auto depuis classe 599) ; 2e POST même créneau → conflit salle ; POST avec lieu différent → OK ; PATCH sans champs lieu → lieu inchangé. `django check` OK, `compileall` OK, `node --check` OK, `flutter analyze` 0 warning nouveau.

- **Nettoyage des affectations héritées en base (2026-08-05)** : 22 enseignants avaient 26-31 classes affectées (354 lignes) héritées de l'ancien import auto — alors qu'ils n'avaient que 2-8 séances. Toutes les `assigned_classes` des `role=teacher` ont été vidées (backup : `teacher_assignments_backup_20260805_192024.json`). Vérifié en direct : `/classes/` → 0 pour tout enseignant, affectation admin → apparition immédiate, retrait → disparition immédiate. Les classes reviennent automatiquement à la création d'une séance (`courses/views.py:79-81`).
- **`StudentSerializer`** (`backend/users/serializers.py`):
  - `create()` lookup par **email** d'abord, puis **code_massar**; si trouvé, met à jour les champs et crée `StudentModuleEnrollment`
  - Conflit de code_massar → `ValidationError`
  - `validate_code_massar()` allégé (uniquement update, exclusion de soi)
  - `code_massar = serializers.CharField()` pour supprimer le `UniqueValidator` automatique de DRF
- **`_process_import_row()`** (`backend/users/services/student_import.py`):
  - Lookup email-first puis code_massar; mise à jour du code_massar si trouvé par email (avec vérification de conflit)
  - `_process_import_row` sauvegarde `code_massar` après modification (`save(update_fields=["code_massar"])`)
- **Test `test_import_rejects_email_linked_to_other_student`** mis à jour : email-match accepté + code_massar mis à jour (au lieu du rejet)
- **7 tests d'import passent** : création, réutilisation email+massar, email+nouveau massar, massar+nouvel email, conflit massar, multiple modules, conflit email

### Restriction des rôles department_head / program_manager
- **`DepartmentSerializer.validate_head()`** (`backend/curriculum/serializers.py`) : seul `role="department_head"` autorisé; rejet si déjà head d'un autre département
- **`FiliereSerializer.validate_manager_id()`** (`backend/curriculum/serializers.py`) : seul `role="program_manager"` autorisé; rejet si déjà manager d'une autre filière
- **`UserCreateSerializer`** et **`UserUpdateSerializer`** (`backend/users/serializers.py`) :
  - Suppression de `is_department_head`, `is_program_manager` (teacher_bridge)
  - `department.head` attribué uniquement si `role == "department_head"`
  - `filiere.manager` attribué uniquement si `role == "program_manager"`
  - Nettoyage automatique lors du changement de rôle

### UI cleanup — checkbox suppression
- **`admin-departments.js`** : `loadDeptHeadSelect()` fetch `/users/?role=department_head` (plus teacher+admin)
- **`admin-departments.js`** : `manageFiliereManagers()` filtre sur `role === 'program_manager'` (plus teacher+program_manager+admin)
- **`admin-filieres.js`** : `loadUsersForManagerSelect()` fetch `/users/?role=program_manager` (plus teacher+admin)
- **`admin.html`** : retrait des champs `uIsAlsoTeacher`, `uIsDeptHead`, `euIsAlsoTeacher`, `euIsDeptHead` des modales add/edit user
- **`admin.html`** : retrait des écouteurs d'événement `uIsDeptHead`, `euIsDeptHead`
- **`admin.html`** : retrait du bloc `is_also_teacher`/`is_department_head` dans `buildPayload`
- **`admin-users.js`** : retrait de `euIsAlsoTeacher`, `euIsDeptHead`, `is_also_teacher`, `is_department_head` dans les blocs `openEditUser()` et `buildPayload()`
- **`admin_users.html`** : retrait des 4 champs `uIsAlsoTeacher`, `uIsDeptHead`, `euIsAlsoTeacher`, `euIsDeptHead`
- **`admin-teachers.js`** : `openEditTeacher()` ne référence plus `tIsDeptHead`/`etIsDeptHead` (utilise les modales `modalAddUser`/`modalEditUser`)
- **`admin_teachers.html`** : retrait des champs `tIsDeptHead`, `etIsDeptHead`
- **`buildPayload` (admin.html)** : retrait des blocs `is_also_teacher`, `is_department_head` pour le rôle teacher

## Tested
- **7 tests d'import étudiant** : tous OK
- **9 tests d'import teacher** : échecs préexistants (`relation "departments" does not exist` dans la DB de test, non lié aux changements)

## Feature: Rapport Excel mensuel — Charge horaire enseignants

### Endpoint
- `GET /api/v1/teacher-monthly-report/` → `teacher_monthly_report` dans `backend/users/views.py`
- Génère un fichier `.xlsx` avec openpyxl

### Filtres (query params)
- `department_id`, `semestre_id`, `filiere_id`, `teacher_id`
- `month` + `year` (ex: month=7, year=2026) **OU** `start_date` + `end_date`

### Calcul
- CM (Cours) = durée réelle (end_time - start_time)
- TD = durée ÷ 1,5
- TP = durée ÷ 1,5
- Seules les séances actives (`is_active=True`) sont comptées

### Colonnes Excel
Enseignant, Département, Filière, Nb séances CM/TD/TP, Total heures CM/TD/TP, Charge horaire totale, Total séances
- Ligne `TOTAL GÉNÉRAL` à la fin
- En-têtes en gras, colonnes ajustées automatiquement
- Nom fichier : `Charge_Horaire_Enseignants_MM_YYYY.xlsx`

### Permissions
- **admin** : tous les enseignants
- **department_head** : enseignants de son département (via `classe.department` ou `classe.filiere.department`)
- **program_manager** : enseignants de sa filière

### Frontend
- `/admin/workload/` → `admin_workload.html` (extends `admin_base.html`)
- `admin-workload.js` : chargement en cascade (semestre → filière, filtre par département), sélecteurs mois/année ou intervalle de dates

## Known Bugs
- Missing teachers import template endpoint: `GET /teachers/import-excel/template/` returns 404.
- Standalone pages (`admin_teachers.html`, `admin_absences.html`, etc.) have broken template blocks (`page_title`, `modals`, `extra_js` not defined in `admin_base.html`).

## Relevant Files
- `backend/users/serializers.py` — StudentSerializer dedup, UserCreateSerializer/UserUpdateSerializer restriction rôles
- `backend/users/services/student_import.py` — _process_import_row email-first lookup, code_massar save
- `backend/curriculum/serializers.py` — DepartmentSerializer.validate_head(), FiliereSerializer.validate_manager_id()
- `backend/templates/admin.html` — modales utilisateur (buildPayload, openEditUser, champs checkbox)
- `backend/templates/admin-users.js` — openEditUser(), buildPayload() cleanup
- `backend/templates/admin-departments.js` — loadDeptHeadSelect(), manageFiliereManagers() role filters
- `backend/templates/admin-filieres.js` — loadUsersForManagerSelect() role filter
- `backend/templates/admin_users.html` — champs checkbox add/edit
- `backend/templates/admin-teachers.js` — openEditTeacher() (utilise modales admin.html)
- `backend/templates/admin_teachers.html` — champs tIsDeptHead/etIsDeptHead (supprimés)
- `backend/users/tests_import.py` — test mis à jour pour email-match+massar update

## Mobile (Flutter) : parit� Enseignant / �tudiant � �tat
- Objectif : replicer le Web pour roles 	eacher et student uniquement (autres roles ? ole_not_supported_screen.dart). Backend/Web inchang�s.
- mobile/lib � 0 erreur et 0 warning lutter analyze (seuls restent des infos withOpacity). lutter test OK. lutter build apk --debug OK.
- Roles rout�s depuis splash_screen.dart / login_screen.dart via _routeForRole.

### Enseignant (espaces complet)
- Dashboard (TeacherDashboardScreen) : carte bienvenue, grille stats globales (pr�sents/absents/taux/�tudiants), s�ances r�centes, pr�sences en direct + bouton refresh + tirer-pour-rafraichir.
- Sync auto : TeacherHomeScreen Timer 30 s -> efreshDashboardLive() sur onglets Accueil/Pr�sences/Stats + refresh au retour foreground (WidgetsBindingObserver). Rechargement apr�s action : SessionsScreen re-ouvre puis efreshSessions() (conserve classe s�lectionn�e).
- S�ances : SessionsScreen (chips classes, liste, �tat temps r�el), SessionFormScreen (cr�ation/edit ; v�rif dispo via _available -> banni�re lieux dispo), reload apr�s retour.
- D�tail s�ance (SessionDetailScreen) : 5 onglets � Pr�sences, Carte(GPS), QR, Statistiques, Suspects. Bouton export feuille de pr�sence XLSX dans l'AppBar.
- Export XLSX : DioClient.downloadBytes() (ResponseType.bytes) + TeacherService.exportSessionXlsx(sessionId) (GET /attendance/session/\{id\}/export/) + FileShareService.shareXlsx() (share_plus). Endpoints ajout�s : sessionExportEndpoint, sessionReportEndpoint.
- Carte GPS : _MapTab (flutter_map + latlong2) affiche les marqueurs des pr�sences (champs latitude/longitude ajout�s � AttendanceModel + SessionAttendance, pars�s depuis ttendance_status/latitude/longitude du serializer).
- QR : onglet QR (current-qr), GenerateQrScreen (expiration, rayon, GPS), closeSession.
- Stats globales : TeacherStatisticsScreen p�riodes 7/30/90 � fix : loadGlobalStats(period) recharge au changement de p�riode.
- Live attendance : TeacherAttendanceScreen (liste scans r�cents) + sync 30 s.

### �tudiant
- StudentHomeScreen 4 onglets (Accueil HomeScreen scan/validation, Emploi du temps, Stats, Profil). Historique : StudentProvider.loadHistory (/attendance/my/). Stats : taux pr�sent calcul� via ttendanceStatus != 'absent' (champ ttendance_status ajout� � AttendanceModel). StudentProfileScreen, StudentScheduleScreen (Cours/Pr�sences).

### Notes / limites
- Pas de DELDT s�ance c�t� Web enseignant : non r�pliqu� (le backend l'expose, mais pas d'UI Web de reference).
- Live temps r�el par polling HTTP 30 s (pas de WebSocket mobil en debut) ; le Web utilise ws /ws/attendance/... � am�lioration future possible.
