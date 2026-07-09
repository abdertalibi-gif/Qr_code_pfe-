# Analyse des Permissions Chef de département

## Résumé
Backend déjà correctement filtré pour `department_head`. Frontend (`admin.html`) corrigé.

## Modifications appliquées

### 1. Backend — `backend/users/permissions.py:21`
`IsAdminOrTeacher` étendu à `admin`, `teacher`, `department_head`
→ Corrige les 403 sur les endpoints curriculum pour department_head

### 2. Frontend — `backend/templates/admin.html`

**`loadAll()`** :
- `loadClasses()`, `loadStudents()`, `loadCurriculum()` → hors `isAdminOnly()`
- `loadDepartmentTeachers()` → `/users/?role=teacher` (filtre automatiquement par département)
- `loadAttendance()`, `setupDepartmentUI()`, `loadLiveOccupation()` → dans `isAdminOnly()`
- `loadAbsenceStats()` → plus admin-only
- `allFilieres` → chargé pour tous

**`updateRoleUI()`** :
- Tabs Chef département : `['sessions', 'curriculum', 'teacher-import', 'classes', 'students', 'absence-stats']`
- Tous les éléments `.admin-only` masqués pour non-admin

**Boutons `admin-only` ajoutés** :
- Tab Enseignants : Nouvel enseignant, Modèle Excel, Importer, Modifier/Désactiver par ligne, panneau import
- Tab Étudiants : Imports étudiants (2 panneaux), Ajouter manuellement
- Tab Classes : Nouvelle classe, Modifier/Supprimer par ligne
- Tab Séances : Nouvelle séance, Supprimer par ligne

### 3. Frontend — `backend/templates/admin-teachers.js`
- `renderTeachers()` : Modifier et Activer/Désactiver → `admin-only`

## Tabs visibles pour Chef département
| Tab | Actions autorisées |
|---|---|
| ✅ Enseignants | Consultation liste uniquement |
| ✅ Étudiants | Consultation liste étudiants du module |
| ✅ Classes | Consultation liste uniquement |
| ✅ Curriculum | Navigation niveaux/semestres/filieres/modules |
| ✅ Séances | Consultation + Export Excel |
| ✅ Statistiques absences | Filtres + Générer Excel (données du département) |

## Confirmations
✓ Aucune table/migration/API créée
✓ Admin conserve tous ses droits et boutons
✓ Chef département voit uniquement consultation + exports filtrés
✓ Logique basée sur le rôle utilisateur
