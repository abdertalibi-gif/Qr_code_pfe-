
## Objective
Complete end-to-end audit of all admin pages: verify data loading, counters, CRUD, modals/buttons, permissions, no errors.
Fix template/JS/API mismatches; add missing pages (Absences, Assistants); add missing dashboard features (Rooms/Amphis tab, Export Wizard data loading); ensure all sidebar counters show real values.

## Key Details
- 5 user roles in forms: admin, teacher, student, department_head, program_manager (with dynamic field visibility)
- Salles & Amphithéâtres management inside admin dashboard (`admin.html`), not just standalone `/admin/rooms/`
- Export Wizard dropdowns fixed to fetch from real API endpoints
- Server: port 8000, admin: admin1@gmail.com / admin123
- Backend APIs: semestres (10), filieres (101), modules (per filiere), classes, teachers (62), attendance counts all working

## Completed
- **Rooms & Amphis dashboard tab**: Added tab button, `tab-rooms` panel with Blocks (expandable room sub-rows), Amphitheaters list, three modals (block/amphi/room CRUD), full JS in `admin.html`. Wired into `loadAll()`. Added `cntRooms` to dashboard counts.
- **User edit modal roles**: Edit User modal now includes all 5 roles.
- **Export Wizard fix**: `openAdminExportWizard` / `bindAdminExportWizardHandlers` fetches semestres, filieres, modules from real APIs; removed `curriculumData` dependency.
- **Git commits**: `a46cb2b` (rooms/amphis + roles), `6413b73` (export wizard fix).
- **Critical JS bugs fixed in `admin.html`**: Removed duplicate `let allBlocks/allAmphis` declarations (SyntaxError), duplicate `loadBlocks()`/`loadAmphitheaters()` functions, duplicate HTML fields in Add User modal (uDepartment, uFiliere, uIsAlsoTeacher, student fields), duplicate `showSpinner()` function.
- **Page templates verified**: `admin_absences.html`, `admin_assistants.html`, `admin_users.html`, `admin_attendances.html`, `admin_teachers.html` all have correct API calls matching backend endpoints.
- **Dashboard room stats added**: 3 hero chips (rooms, blocks, amphitheaters) and 3 stat cards in the rooms tab panel, wired into `loadDashboardCounts()`. Added `.stat-icon.teal` CSS class.
- **Teachers tab in dashboard**: Renamed "Import enseignants" → "Enseignants", moved to position 3. Reused `admin-teachers.js` (load via `<script src>`). Fixed JS naming conflicts (`teacherDepartments`, `teacherFilieres`, `teacherClasses`, `teacherLoadDepartments/Filieres/Classes`). Added teacher table, search, CRUD modals, import panel into `tab-teacher-import`. Fixed `heroUserCount` never populated. Fixed `updateRoleUI` missing `teacher-import` and `rooms` in `allTabs`.
- **Statistiques des absences tab**: Added 10th tab (`absence-stats`) with 8 stat cards, 6 data sub-tabs (student/teacher/module/filiere/period/recent), 4 chart types (histogram/pie/line/bar), date/filiere/module/teacher filters, Excel/PDF export. Wired into `loadAll()` and `updateRoleUI()`.
- **Fixed `/api/v1/statistics/` endpoint**: Changed `timestamp` → `validation_time` in all queries + `.extra()` calls.
- **Fixed CSV/PDF exports**: Fixed field name references to match `_build_export_rows()` output; corrected column widths.
- **New API `/api/v1/absence-stats/`**: Returns summary (8 stats), by_student (top 30), by_teacher, by_module, by_filiere, by_day, by_week, recent_absences (50). Supports filters: date_from, date_to, filiere_id, module_id, teacher_id.
- **Chart.js CDN** added to admin.html.
- **Gestion des salles tab**: Restructured with 4 sub-tabs (Blocs/Salles/Amphis/Occupation), 7 stat cards, occupation live view (15s auto-refresh), reused existing CRUD modals.
- **Department buttons (Gérer/Modifier) fixed**: 3 bugs corrected in `admin.html` — (1) `openDepartmentModal()` now `async` with `await loadDeptHeadSelect()` so the head is pre-selected; (2) replaced `addEventListener` with `onclick` on `btnSaveFiliereManagers` to prevent duplicate listeners; (3) modal only closes on success (not on partial failure). Added debug `console.log` statements.
- **Debounce locks added**: `_managersLoading` + `_editingDeptLoading` flags prevent duplicate calls when user clicks rapidly on Gérer/Modifier buttons.

## Files Modified
- `backend/templates/admin.html` — rooms/amphis tab, modals, JS; Export Wizard rewrite; edit user modal 5 roles; fixed duplicate let/function/HTML field bugs; added room/block/amphi hero chips and stat cards; Enseignants tab (reused admin-teachers.js, expanded panel, added modals); fixed heroUserCount; fixed updateRoleUI allowedTabs; added Chart.js CDN; added absence-stats tab button/panel/JS (8 stat cards, 6 sub-tabs, 4 charts, filters, export, `loadAbsenceStats()`, `setupAbsenceSubTabNavigation()`, `populateAbsenceFilters()`)
- `backend/templates/admin_users.html` — complete 5-role form with dynamic fields
- `backend/templates/admin-users.js` — full 5-role CRUD with dynamic field visibility
- `backend/templates/admin_absences.html` — absence listing with date/search filters
- `backend/templates/admin-absences.js` — absence data loading, filtering by absent status
- `backend/templates/admin_assistants.html` — assistants listing
- `backend/templates/admin-assistants.js` — assistants data loading, is_also_teacher filter
- `backend/users/views.py` — teacher_list, block_list, room_list, amphitheater_list, dashboard_counts; FIXED `admin_statistics` (timestamp→validation_time); ADDED `absence_statistics` view; FIXED teacher_list (retiré filtrage scope, prefetch_related optimisé, retourne 115 enseignants)
- `backend/curriculum/views.py` — semestre_list, filiere_list, module_list, niveau_list
- `backend/config/urls.py` — routes for blocks/, rooms/, amphitheaters/, curriculum/ endpoints; ADDED `absence-stats/` route
- `backend/templates/admin_base.html` — added 3 missing template blocks (`page_title`, `modals`, `extra_js`) for standalone pages
- `backend/templates/dashboard.css` — added `.stat-icon.teal` CSS class
- `backend/templates/admin-teachers.js` — renamed conflicting functions/vars with `teacher` prefix; added `initTeachersTab()`
- `backend/attendance/views.py` — FIXED CSV/PDF exports (`_export_csv`, `_export_pdf` field names & column widths)

## Known Bugs (remaining)
1. ~~**`/api/v1/statistics/` endpoint BROKEN** — uses `timestamp` instead of `validation_time` → FieldError.~~ **FIXED**
2. ~~**CSV/PDF exports broken** — `_export_csv()` and `_export_pdf()` reference field names not produced by `_build_export_rows()`.~~ **FIXED**
3. ~~**No Chart.js or charting library** anywhere in the project.~~ **FIXED** (added CDN)
4. ~~**Missing teachers import template endpoint** — `GET /teachers/import-excel/template/` returns 404.~~ **NOT A BUG** — endpoint fonctionne (HTTP 200, 6269 bytes, testé via serveur réel).
5. ~~**Standalone pages** (`admin_teachers.html`, `admin_absences.html`, etc.) have broken template blocks (`page_title`, `modals`, `extra_js` not defined in `admin_base.html`).~~ **FIXED** — ajouté les 3 blocs manquants dans `admin_base.html`.
6. ~~**Teacher dropdowns empty across ALL forms** — `apply_role_filtering` exclut les enseignants sans relations `assigned_classes`/`sessions`/`taught_modules`. 117 teachers, dont seulement 21 avec assigned_classes et 3 matchent les filières du PM.~~ **FIXED** — `teacher_list()` ne filtre plus par scope ; retourne tous les 117 enseignants actifs.

## Fixed

### BUG teacher dropdowns vides — **FIXED** (this session)
- **Cause racine** : `teacher_list()` (GET /teachers/) appliquait `apply_role_filtering` avec les relations `assigned_classes`/`sessions`/`taught_modules`. Sur 117 enseignants, seuls 21 avaient des `assigned_classes`, 16 des sessions, 0 des modules. Pour le program_manager, seulement **3** enseignants matchaient ses filières.
- **Fix** : Retiré le filtrage scope de `teacher_list()` dans `backend/users/views.py:504`. L'endpoint retourne désormais tous les enseignants actifs (117), sans filtre de rôle. Les endpoints concernés : `session_form.js` (formulaire séance), export wizard, absence stats.
- **Note** : `/users/?role=teacher` (UserViewSet) garde son filtrage scope pour la page de gestion des enseignants.
- **Optimisation** : ajout `prefetch_related(Prefetch("assigned_classes", queryset=Classe.objects.select_related("department", "filiere__department")))` pour éviter N+1 requêtes (345 requêtes → 3 requêtes).
- **Testé** : `GET /api/v1/teachers/` via serveur réel → HTTP 200, 115 enseignants retournés pour admin.

## Department Buttons Analysis (Gérer / Modifier) — **FIXED**

### Bug 1 — Modifier : chef jamais pré-sélectionné
- **Fix** : `openDepartmentModal()` → `async` + `await loadDeptHeadSelect()` — le chef est pré-sélectionné.
### Bug 2 — Gérer : listeners multiples sur btnSaveFiliereManagers
- **Fix** : Remplacé `addEventListener` par `onclick = saveFiliereManagers`.
### Bug 3 — Gérer : modal fermé même en cas d'échec
- **Fix** : `classList.remove('show')` déplacé dans le bloc `else` (succès seulement).
