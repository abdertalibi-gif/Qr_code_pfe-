# Système de Gestion des Présences par QR Code

## Projet de Fin d'Études

---

## 1. Présentation du Projet

### 1.1 Contexte

Ce projet est un **système de gestion des présences** universitaire utilisant la **technologie QR code**. Il permet aux enseignants de générer des QR codes dynamiques pendant leurs séances, aux étudiants de valider leur présence en scannant ces codes, et aux administrateurs de superviser l'ensemble du processus.

### 1.2 Objectifs

- **Numérisation** du processus de prise de présence
- **Sécurisation** par QR code dynamique avec expiration, géolocalisation et anti-fraude
- **Gestion des rôles** : Admin, Enseignant, Étudiant, Chef de département, Responsable de filière
- **Tableau de bord** en temps réel avec statistiques et exports
- **Application mobile** Flutter pour le scan QR et la validation

---

## 2. Architecture du Système

```
┌─────────────────────────────────────────────────────────────┐
│                    NAVIGATEUR WEB (SPA)                      │
│  admin.html (10 tabs) │ teacher.html │ student.html │ attend │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / JWT
┌──────────────────────────▼──────────────────────────────────┐
│              API REST Django (port 8000)                     │
│  ~45 endpoints : auth, users, classes, sessions, attendance │
│  WebSocket (Daphne) : présence en direct                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                Base de Données PostgreSQL                     │
│  429 users │ 6 départements │ 101 filières │ 45 classes     │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Application Mobile Flutter                      │
│  Scan QR │ Validation │ Géolocalisation │ Historique        │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Stack Technique

| Couche | Technologie | Version |
|--------|-------------|---------|
| Backend | Django | 6.0.5 |
| API | Django REST Framework | 3.15+ |
| Auth | djangorestframework-simplejwt | 5.3.1 |
| Base de données | PostgreSQL (Neon) / SQLite3 | — |
| Serveur ASGI | Daphne | 4.1.2 |
| WebSocket | Django Channels | 4.1.0 |
| Frontend Web | HTML + CSS + JS vanilla (SPA) | — |
| Graphiques | Chart.js (CDN) | — |
| Mobile | Flutter / Dart | — |
| Scanner QR | mobile_scanner | ^7.0.0 |
| Géolocalisation | geolocator | ^13.0.2 |
| Export Excel | openpyxl | 3.1.5 |
| Export PDF | Django + report | — |
| API Docs | drf-yasg (Swagger/Redoc) | 1.21.8 |

---

## 3. Modèle de Données

### 3.1 Diagramme des Entités

```
User ──1:1──► Student
 │
 ├──M:N──► Classe (assigned_classes, related_name="teachers")
 │
 ├──1:N──► Session (teacher)
 │
 ├──1:N──► Department (head)  ← headed_department
 │
 └──M:N──► Filiere (manager)  ← managed_filieres

Department ──1:N──► Filiere

Filiere ──1:N──► Module

Classe ──N:1──► Filiere
Classe ──N:1──► Semestre
Classe ──N:1──► Module
Classe ──N:1──► Block / Room / Amphitheater

Session ──N:1──► Classe
Session ──N:1──► Module
Session ──N:1──► User (teacher)

Attendance ──N:1──► Student
Attendance ──N:1──► Session

SuspiciousAttempt ──N:1──► Session
```

### 3.2 Applications Django

Le projet est organisé en **4 applications** :

| Application | Rôle |
|-------------|------|
| `users` | Authentification, utilisateurs, départements, salles, classes, étudiants |
| `curriculum` | Semestres, filières, modules |
| `courses` | Séances (sessions) |
| `attendance` | Présences, tentatives suspectes, exports, WebSocket |

### 3.3 Statistiques de la Base

| Entité | Quantité |
|--------|----------|
| Utilisateurs | 429 |
| ├── Admin | 1 |
| ├── Enseignants | 114 |
| ├── Étudiants | 287 |
| ├── Chefs de département | 7 |
| └── Responsables de filière | 20 |
| Départements | 6 |
| Filières | 101 |
| Modules | 641 |
| Semestres | 10 (S1–S10) |
| Classes | 45 |
| Séances | 74 |
| Présences enregistrées | 513 |
| Blocs / Salles / Amphis | 10 / 78 / 8 |

---

## 4. API REST

### 4.1 Points d'entrée principaux (~45 endpoints)

**Authentification :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/auth/login/` | Connexion (JWT) |
| POST | `/api/v1/auth/refresh/` | Rafraîchir le token |
| GET | `/api/v1/auth/me/` | Profil utilisateur |

**Gestion des utilisateurs :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET/POST | `/api/v1/users/` | Lister/créer des utilisateurs |
| GET/PUT/PATCH/DELETE | `/api/v1/users/{id}/` | Détail/modifier/supprimer |
| POST | `/api/v1/users/{id}/toggle-active/` | Activer/désactiver |

**Présences :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/attendance/validate/` | Valider présence (Web) |
| POST | `/api/v1/attendance/validate/app/` | Valider présence (App) |
| GET | `/api/v1/attendance/my/` | Mes présences |
| GET | `/api/v1/attendance/session/{id}/stats/` | Statistiques d'une séance |
| GET | `/api/v1/attendance/export-wizard/` | Export avancé (filtres) |
| GET | `/api/v1/absence-stats/` | Statistiques globales d'absences |

### 4.2 Authentification JWT

- **Token d'accès** : 1 heure de validité
- **Token de rafraîchissement** : 7 jours (rotation activée)
- **Header** : `Authorization: Bearer <token>`
- **Rate limiting** : 30 req/min (anonyme), 120 req/min (authentifié)

### 4.3 Permissions (5 rôles)

| Rôle | Accès |
|------|-------|
| `admin` | Accès complet à toutes les fonctionnalités |
| `department_head` | Accès limité aux données de son département |
| `program_manager` | Accès limité aux données de ses filières |
| `teacher` | Gestion des séances, génération QR, listes d'appel |
| `student` | Validation de présence par QR (Web + App) |

---

## 5. Interface Web (SPA)

### 5.1 Dashboard Admin (`admin.html`)

Single Page Application avec **10 onglets** :

| # | Onglet | Fonctionnalités |
|---|--------|-----------------|
| 1 | **Présences en direct** | Tableau live (WebSocket), vue admin, filtres |
| 2 | **Utilisateurs** | CRUD complet, 5 rôles, activation/désactivation |
| 3 | **Enseignants** | Gestion, import Excel, recherche |
| 4 | **Étudiants** | Gestion, import Excel, inscription aux modules |
| 5 | **Classes** | Création, filtres par filière/semestre |
| 6 | **Curriculum** | Semestres, filières, modules, niveaux |
| 7 | **Séances** | Programmation, affectation salles, QR |
| 8 | **Départements** | Gestion, chefs, filières associées |
| 9 | **Salles** | Blocs, salles, amphis, occupation en direct |
| 10 | **Statistiques absences** | 8 cartes, 6 sous-onglets, 4 types de graphiques |

### 5.2 Pages spécifiques

| Page | Rôle | Description |
|------|------|-------------|
| `/teacher/` | Enseignant | Dashboard enseignant avec séances |
| `/student/` | Étudiant | Dashboard étudiant avec historique |
| `/attend/` | Tous | Page de validation QR |

### 5.3 Fichiers JS (18 fichiers)

Chaque module d'administration dispose de son propre fichier JavaScript :
- `api.js` — Configuration API, gestion des tokens, requêtes HTTP
- `admin-users.js` — CRUD utilisateurs
- `admin-teachers.js` — Gestion des enseignants
- `admin-classes.js` — Gestion des classes
- `admin-curriculum.js` — Gestion du curriculum
- `admin-sessions.js` — Gestion des séances
- `admin-rooms.js` — Gestion des salles et amphis
- ...

---

## 6. Application Mobile (Flutter)

L'application mobile permet aux étudiants de valider leur présence via scan QR.

### 6.1 Fonctionnalités

- Scan de QR code avec la caméra
- Validation de présence avec géolocalisation
- Historique des présences
- Détection anti-fraude (même appareil, même IP, etc.)

### 6.2 Dépendances principales

| Package | Version | Usage |
|---------|---------|-------|
| `mobile_scanner` | ^7.0.0 | Scan QR code |
| `geolocator` | ^13.0.2 | Géolocalisation |
| `dio` | ^5.7.0 | Requêtes HTTP |
| `provider` | ^6.1.2 | Gestion d'état |
| `device_info_plus` | ^11.2.0 | Empreinte appareil |

---

## 7. Sécurité

### 7.1 Mécanismes anti-fraude

1. **QR dynamique** : Token unique avec expiration (défaut 30s)
2. **Géolocalisation** : Vérification du rayon de proximité
3. **Empreinte appareil** : `device_id` + `device_fingerprint`
4. **Détection des anomalies** :
   - Même étudiant scannant plusieurs fois
   - Même appareil utilisé par plusieurs étudiants
   - QR expiré ou déjà utilisé
   - Violation de géofence
   - Connexions simultanées depuis des IP différentes

### 7.2 Journalisation des tentatives suspectes

Toutes les anomalies sont enregistrées dans la table `SuspiciousAttempt` avec :
- Type d'anomalie (10 types différents)
- Métadonnées : IP, appareil, position, token
- Horodatage précis

---

## 8. Export et Rapports

### 8.1 Formats supportés

| Format | Export Wizard | Rapports séance |
|--------|---------------|-----------------|
| Excel (.xlsx) | ✅ | ✅ |
| PDF | ✅ | ✅ |
| CSV | ✅ | — |
| JSON | ✅ | — |

### 8.2 Filtres disponibles (Export Wizard)

- Semestre
- Filière
- Module
- Classe
- Enseignant
- Période (date_from, date_to)

---

## 9. Travaux réalisés (Synthèse)

### 9.1 Corrections et optimisations backend

| Correction | Description |
|------------|-------------|
| **Endpoint `/api/v1/statistics/`** | Remplacement de `timestamp` par `validation_time` |
| **Exports CSV/PDF** | Correction des noms de champs et largeurs de colonnes |
| **API `/api/v1/absence-stats/`** | Nouvel endpoint avec 8 statistiques et filtres |
| **Permissions** | Ajout de `apply_role_filtering()` pour chaque modèle |
| **Rôles en base** | Correction de 10 comptes avec rôles incorrects |
| **Dashboard counts** | Ajout des compteurs salles, blocs, amphis |

### 9.2 Fonctionnalités ajoutées

| Fonctionnalité | Composants |
|----------------|------------|
| **Onglet Salles** | 4 sous-onglets (Blocs/Salles/Amphis/Occupation), 7 cartes stats |
| **Onglet Statistiques absences** | 8 cartes, 6 sous-onglets, 4 types de graphiques, filtres |
| **Export Wizard** | Chargement dynamique semestres/filières/modules depuis l'API |
| **Gestion des départements** | Boutons Gérer/Modifier avec pré-sélection du chef |
| **5 rôles** | Admin, Enseignant, Étudiant, Chef de département, Responsable filière |

---

## 10. Guide de démarrage

### 10.1 Prérequis

- Python 3.12+
- Flutter (pour l'application mobile)
- Base de données PostgreSQL (ou SQLite3 par défaut)

### 10.2 Installation

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # ou .\venv\Scripts\activate (Windows)
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver

# Mobile (optionnel)
cd mobile
flutter pub get
flutter run
```

### 10.3 Comptes par défaut

| Email | Rôle | Mot de passe |
|-------|------|-------------|
| admin@admin.com | Admin | admin123 |
| (créer utilisateur) | Enseignant | Défini lors de la création |
| (créer utilisateur) | Étudiant | Défini lors de la création |
| (créer utilisateur) | Chef de département | Défini lors de la création |
| (créer utilisateur) | Resp. filière | Défini lors de la création |

---

## 11. Conclusion

Ce système de gestion des présences par QR code répond aux besoins d'une université moderne. Il offre :

- **Une solution complète** : Web + Mobile
- **Une sécurité renforcée** : QR dynamique, géolocalisation, anti-fraude
- **Une gestion fine des rôles** : 5 profils avec permissions granulaires
- **Des exports professionnels** : Excel, PDF, CSV
- **Un suivi en temps réel** : WebSocket, statistiques, graphiques

L'architecture Django REST + SPA vanilla permet une maintenance aisée et des performances optimales, tandis que l'application mobile Flutter offre une expérience utilisateur fluide pour la validation des présences.
