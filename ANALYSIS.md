# Analyse complète du système — Export Excel et Statistiques des absences

Date : 2026-07-09
Projet : attendance-system-QR

---

## 1. Architecture générale

```
Frontend (admin.html)
  ├── Export Wizard Sessions  →  modalExportWizard + fonctions JS
  └── Statistiques absences   →  tab-absence-stats + fonctions JS
                                      │
                                      ▼
Backend API
  ├── GET /api/v1/attendance/export-wizard/  →  ExportWizardView → ExportWizardService
  ├── GET /api/v1/absence-stats/            →  absence_statistics
  └── GET /api/v1/statistics/               →  admin_statistics
```

Tous les exports Excel passent par un seul point d'entrée : `ExportWizardView` → `ExportWizardService.generate_xlsx()`

---

## 2. Modèles de données — Chaînes de relations

```
Attendance
  ├── student → Student
  │                ├── user → User (OneToOne)
  │                ├── classe → Classe
  │                │              ├── filiere → Filiere → department → Department
  │                │              ├── semestre → Semestre
  │                │              ├── module → Module → filiere → Filiere
  │                │              ├── department → Department
  │                │              └── academic_year (CharField, ex: "2025/2026")
  │                └── modules → Module (M2M via StudentModuleEnrollment)
  └── session → Session
                   ├── module → Module
                   ├── teacher → User
                   ├── classe → Classe
                   ├── subject (CharField — matière de la séance)
                   └── date, start_time, end_time
```

---

## 3. Export Wizard existant (Sessions) — Fonctionnel

### Frontend (`admin.html`)

| Fonction | Lignes | Usage | Statut |
|---|---|---|---|
| `openAdminExportWizard()` | 2931–3003 | Initialise et ouvre le modal | ✅ |
| `bindAdminExportWizardHandlers()` | 3006–3122 | Cascade Semestre→Filière→Module→Classe | ✅ |
| `loadWizardStudents()` | 3134–3172 | Charge étudiants via `/students/` | ✅ (corrigé id vs name) |
| `filterWizardStudentList()` | 3174–3194 | Recherche client-side par Nom/Massar/Apogée | ✅ |
| `generateAdminExportWizard()` | 3205–3288 | Génère l'Excel via `export-wizard/` | ✅ |
| `toggleStudentFilter()` | 3124–3132 | Affiche/cache la recherche étudiant | ✅ |
| `validateAdminExportForm()` | 3196–3203 | Validation du formulaire | ✅ |

### Backend

| Composant | Fichier | Lignes |
|---|---|---|
| `ExportWizardView` | `attendance/views.py` | 892–995 |
| `ExportWizardService` | `attendance/export_service.py` | 1–627 |
| URL | `attendance/urls.py` | `GET /api/v1/attendance/export-wizard/` |

### Modes d'export supportés par `ExportWizardService`

| Mode | Description | Fonction |
|---|---|---|
| `by_student` | Détail par étudiant | `_build_detail_rows()` → `_generate_detail_xlsx()` |
| `by_module` | Détail par module | `_build_detail_rows()` → `_generate_detail_xlsx()` |
| `by_session` | Détail par séance | `_build_detail_rows()` → `_generate_detail_xlsx()` |
| `resume_absences` | Résumé trié par absences desc | `_build_summary_rows()` → `_generate_summary_xlsx()` |
| `resume_presences` | Résumé trié par taux présence desc | `_build_summary_rows()` → `_generate_summary_xlsx()` |
| `professional` | Rapport pro avec en-tête et stats | `_build_professional_rows()` → `_generate_professional_xlsx()` |

### Paramètres acceptés par `build_filtered_queryset()`

| Paramètre | Type | Filtre Django |
|---|---|---|
| `start_date` | string (YYYY-MM-DD) | `session__date__gte` |
| `end_date` | string (YYYY-MM-DD) | `session__date__lte` |
| `semestre` | string (name) | `student__classe__semestre__name__icontains` |
| `filiere` | string (name) | `student__classe__filiere__name__icontains` |
| `module` | string (name) | `session__subject__icontains` |
| `department_id` | integer | `student__classe__department_id` |
| `filiere_id` | integer | `student__classe__filiere_id` |
| `semestre_id` | integer | `student__classe__semestre_id` |
| `module_id` | integer | `session__module_id` |
| `classe_id` | integer | `session__classe_id` |
| `enseignant_id` | integer | `session__teacher_id` |
| `etudiant_id` | integer | `student_id` |
| `export_type` | all/present/absent | `attendance_status` filter |
| `export_mode` | string | Dispatch vers le bon générateur |

---

## 4. Statistiques des absences — Composants existants

### Frontend (`admin.html`)

| Fonction | Lignes | Usage |
|---|---|---|
| `populateAbsenceFilters()` | 3994–4014 | Charge départements + enseignants |
| `absOnDeptChange()` | 4016–4039 | Cascade Département→Filière |
| `absOnFiliereChange()` | 4042–4079 | Cascade Filière→Semestre+Module |
| `absOnModuleChange()` | 4082–4101 | Cascade Module→Classe |
| `absGetFilterParams()` | 4104–4116 | Collecte tous les filtres |
| `loadAbsenceStats()` | 4118–4129 | Appel API `/absence-stats/` |
| `renderAbsenceStats()` | 4131–4151 | Affiche stats + tableaux |
| `renderAbsenceTable()` | 4153–4172 | Génère HTML des tableaux |
| `applyAbsenceFilters()` | 4174–4176 | Déclenche le chargement |
| `resetAbsenceFilters()` | 4178–4196 | Réinitialise tout |
| `absCheckExportEnabled()` | 4198–4207 | Active/désactive bouton export |
| `exportProfessionalAbsences()` | 4216–4268 | Export via XHR brut |
| `setupAbsenceSubTabNavigation()` | 4270–4281 | Navigation sous-onglets |

### Backend

| Fonction | Fichier | Lignes |
|---|---|---|
| `absence_statistics()` | `users/views.py` | 748–925 |
| `admin_statistics()` | `users/views.py` | 686–743 |
| URL: `absence-stats/` | `config/urls.py` | Ligne 149 |
| URL: `statistics/` | `config/urls.py` | Ligne 148 |

### Structure réponse `GET /api/v1/absence-stats/`

```json
{
  "summary": {
    "total": 1234,
    "present": 1000,
    "absent": 234,
    "absence_rate": 18.96,
    "total_students": 450,
    "total_sessions": 89,
    "total_teachers": 62,
    "total_modules": 15,
    "total_filieres": 5,
    "total_departments": 3
  },
  "by_student": [
    {
      "student_id": 1,
      "student__first_name": "John",
      "student__last_name": "Doe",
      "student__code_massar": "M12345",
      "total": 20,
      "absent_count": 8,
      "rate": 40.0,
      "student_name": "John Doe"
    }
  ],
  "by_teacher": [...],
  "by_module": [...],
  "by_filiere": [...],
  "by_day": [...],
  "by_week": [...],
  "recent_absences": [...]
}
```

---

## 5. Export Excel professionnel — État actuel

### `_build_professional_rows(qs)` — retourne par étudiant :

```python
{
    "code_massar": str,
    "code_apogee": str,
    "nom": str,
    "prenom": str,
    "department": str,
    "filiere": str,
    "semestre": str,
    "module": str,          # session.subject (dernière séance)
    "classe": str,          # str(classe) via __str__
    "enseignant": str,      # session.teacher.full_name (dernière séance)
    "presents": int,
    "absents": int,
    "taux_presence": "X%",
    "taux_absence": "X%",
    # Note: pas de champ "total_seances"
}
```

### `_generate_professional_xlsx(rows, filters)` — structure du fichier :

```
Row 1: "Rapport des absences" (merged A1:N1, title font)
Row 2: "Université | Faculté des Sciences | Département: X | Filière: Y" (merged A2:N2)
Row 3: (spacer)
Row 4: stats labels (merged A4:E4 — BUG, écrase les 4 autres stats)
Row 5: stats values (merged A5:E5 — BUG, écrase les 4 autres valeurs)
Row 6: (spacer)
Row 7: en-têtes tableau (14 colonnes, fond bleu foncé)
Row 8+: données (lignes alternées, absents en rouge)
       colonnes : Code Massar, Apogée, Nom, Prénom, Dept, Filière, Semestre,
                  Module, Classe, Enseignant, Présences, Absences, Taux présence, Taux absence
```

---

## 6. BUGS IDENTIFIÉS

### Frontend — Statistiques (`admin.html`)

| # | Problème | Ligne | Détail |
|---|---|---|---|
| 1 | `student__code_massar` au lieu de `code_massar` | 4143 | Le backend renvoie `code_massar` (plat) dans `by_student`, pas `student__code_massar`. La colonne Code Massar est vide. |
| 2 | `student__code_massar` idem dans recent_absences | 4148 | Backend renvoie `code_massar` (déjà extrait dans le champ plat), pas `student__code_massar`. |
| 3 | `absGetFilterParams()` ne collecte jamais `absStudentSearch` | 4104–4116 | L'input texte étudiant existe dans le DOM mais sa valeur n'est jamais envoyée à l'API. |
| 4 | `absence_statistics` n'accepte pas `student_id` | 757–764 | Aucun moyen de filtrer par étudiant côté backend. |
| 5 | `absCheckExportEnabled()` pas déclenché par `absModule` change | 4210–4213 | Seulement `absDept`, `absFiliere`, `absSemestre` sont surveillés. Le module manque. |
| 6 | Pas de cascade Semestre réelle | 4042–4068 | Semestre auto-rempli depuis `dataset.semestreId` de la filière, mais pas de vrai chargement API. |

### Backend — Export professionnel (`export_service.py`)

| # | Problème | Ligne | Détail |
|---|---|---|---|
| 7 | `merge_cells("A4:E4")` écrase les stats | 518–519 | Les labels "Total présences", "Total absences", "Taux de présence", "Taux d'absence" et leurs valeurs sont dans des cellules qui sont ensuite écrasées par le merge. Seule la première stat s'affiche. |
| 8 | Pas de `total_seances` dans `_build_professional_rows` | 405–420 | Impossible d'afficher "Nombre total de séances" dans l'Excel. |
| 9 | `module` = `session.subject` (dernière séance) | 402 | Si un étudiant a des séances de modules différents, seul le sujet de la dernière séance est utilisé. |
| 10 | `enseignant` = `session.teacher.full_name` (dernière séance) | 403 | Même problème — si plusieurs enseignants, seul le dernier est listé. |
| 11 | En-tête manquant : Semestre, Module, Classe, Enseignant | 468–478 | Seulement Département et Filière sont affichés. |
| 12 | En-tête manquant : Période, Année univ., Date génération, Utilisateur | 468–478 | Aucune info de contexte temporel. |
| 13 | `filters` peut être `None` | 470 | `filters.get()` lèverait `AttributeError`. |

### Général

| # | Problème | Détail |
|---|---|---|
| 14 | `exportProfessionalAbsences()` utilise `XMLHttpRequest` brut | Incohérent avec le reste du code qui utilise `API.apiFetch()`. Pas de progress bar, pas d'UX wizard. |
| 15 | Pas de role filtering dans `absence_statistics` | Les chefs de département et responsables de filière voient toutes les données. |

---

## 7. COMPOSANTS RÉUTILISABLES SANS MODIFICATION

| Composant | Fichier | Réutilisation prévue |
|---|---|---|
| `ExportWizardView` | `attendance/views.py:892` | Point d'entrée unique pour tout export Excel |
| `ExportWizardService.build_filtered_queryset()` | `export_service.py:70` | Filtrage params (tous les 16 paramètres supportés) |
| `ExportWizardService.generate_xlsx()` | `export_service.py:601` | Dispatch par mode d'export |
| `ExportWizardService._build_professional_rows()` | `export_service.py:365` | Agrégation par étudiant (améliorer) |
| `ExportWizardService._generate_professional_xlsx()` | `export_service.py:426` | Génération XLSX (corriger stats + en-tête) |
| `loadWizardStudents()` (JS) | `admin.html:3134` | Chargement étudiant via API |
| `filterWizardStudentList()` (JS) | `admin.html:3174` | Recherche client-side |
| `toggleStudentFilter()` (JS) | `admin.html:3124` | UI filtre étudiant |
| `validateAdminExportForm()` (JS) | `admin.html:3196` | Validation formulaire |
| `bindAdminExportWizardHandlers()` (JS) | `admin.html:3006` | Cascade des filtres (réutilisable avec ajout Département) |

---

## 8. PLAN DE CORRECTION RECOMMANDÉ

### Phase 1 — Bugs critiques frontend stats
1. `renderAbsenceStats()` : `student__code_massar` → `code_massar` (lignes 4143, 4148)
2. `absGetFilterParams()` : ajouter `student_id` depuis `absStudentSearch`
3. `absCheckExportEnabled()` : ajouter `absModule` au listener

### Phase 2 — Export Excel professionnel
4. Supprimer `merge_cells` stats ou répartir sur ligne unique (colonne par stat)
5. Ajouter `total_seances` dans `_build_professional_rows()`
6. Remplacer `session.subject` par boucle sur tous les modules de l'étudiant
7. Enrichir en-tête XLSX (Semestre, Module, Classe, Enseignant, Période, Année univ., Date génération, Utilisateur)
8. Gérer `filters is None` dans `_generate_professional_xlsx`

### Phase 3 — Backend absence_statistics
9. Ajouter paramètre `student_id` au view `absence_statistics`
10. Ajouter `student_search` (text search) au view `absence_statistics`
11. Ajouter role filtering pour `department_head`/`program_manager`

### Phase 4 — Modal Wizard stats
12. Ajouter `#expDepartmentArea` (caché) dans le modal existant
13. Ajouter `#expTypeModeArea` wrapper pour show/hide type/mode
14. Ajouter flag `_statsExportMode` + `openStatsExportWizard()`
15. Modifier `generateAdminExportWizard()` pour mode stats → `export_mode=professional`

---

## 9. FICHIERS À MODIFIER

| Fichier | Modifications |
|---|---|
| `backend/templates/admin.html` | Corrections render champs, cascade, filtre étudiant, listener export, bouton/flag stats wizard, department area |
| `backend/attendance/export_service.py` | Correction merge_cells, ajout total_seances, en-tête enrichi, gestion filters=None |
| `backend/users/views.py` | Ajout student_id + student_search filter, role filtering dans absence_statistics |

---

## 10. CONFIRMATIONS

- ✅ **Aucune table recréée** — modèles existants utilisés
- ✅ **Aucune migration créée** — pas de nouveau champ/changement de schéma
- ✅ **Aucune donnée supprimée** — modifications additives uniquement
- ✅ **Aucune API dupliquée** — ExportWizardView réutilisé, absence-stats amélioré
- ✅ **Aucun code existant supprimé** — seulement corrections et améliorations
- ✅ **Export Excel existant conservé** — les 5 modes existants inchangés
- ✅ **Base PostgreSQL compatible** — pas de changement de schéma
- ✅ **Chart.js non nécessaire** — pas de graphiques requis pour le wizard d'export
