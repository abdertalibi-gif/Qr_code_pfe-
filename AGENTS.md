
## Objective
- Un étudiant = un email unique ou un Code Massar unique dans la base. Pas de doublons.
- Un étudiant peut être inscrit dans plusieurs modules, semestres et années universitaires.
- Réutilisation des fiches existantes, mise à jour des inscriptions uniquement.
- Seuls les utilisateurs avec `role=department_head` peuvent être chefs de département.
- Seuls les utilisateurs avec `role=program_manager` peuvent être responsables de filière.
- Suppression de la passerelle enseignant → chef de département / responsable filière.

## Key Details
- 5 user roles: admin, teacher, student, department_head, program_manager (dynamic field visibility)
- Server: 8000, admin: admin@umi.ac.ma / test1234
- Real DB: PostgreSQL (Neon)
- Student model: `email` (not unique), `code_massar` (unique=True), `classe` (FK → Classe), `modules` (M2M via StudentModuleEnrollment)
- `Department.head` et `Filiere.manager` sont des ForeignKey vers User — validation du rôle dans les serializers.
- Pas de migrations, pas de changement de schéma.

## Completed

### Student deduplication (serializer + import)
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
