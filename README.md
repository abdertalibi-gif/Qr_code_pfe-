# PrésenceQR — Gestion des présences par QR code

Application de suivi des présences étudiantes basée sur un code QR, composée d’un **backend Django REST Framework**, d’une **interface web** (administration, enseignants, étudiants) et d’une **application mobile Flutter**.

Le système couvre les filières, niveaux, modules, classes, séances, enseignants et étudiants, avec génération de QR codes, scan côté mobile, suivi en direct par WebSocket, détection des tentatives suspectes et export des présences au format Excel.

---

## Fonctionnalités principales

- **Administration** : gestion des utilisateurs et des rôles, classes, filières/niveaux/modules, séances, salles, blocs, amphithéâtres, départements, statistiques et rapports.
- **Enseignants** : création de séances, génération du QR code, suivi des présences en direct, import des enseignants depuis Excel, charge horaire et rapports mensuels.
- **Étudiants** : consultation de l’emploi du temps et des séances, marquage de la présence par scan du QR code.
- **Sécurité des scans** : identification de l’appareil, limitation des doubles scans, géolocalisation facultative et journal des tentatives suspectes.
- **Temps réel** : WebSockets pour les présences live (enseignant et administrateur) et les mises à jour d’emploi du temps.
- **API documentée** : authentification JWT (SimpleJWT) et documentation Swagger.

---

## Structure du dépôt

```text
.
├── backend/                 # Projet Django (config, apps, templates, static, médias)
│   ├── config/              # settings.py, urls.py, asgi.py (Channels/Daphne)
│   ├── attendance/          # Présences, QR codes, WebSockets, rapports
│   ├── courses/             # Séances et planification
│   ├── curriculum/          # Filières, niveaux, modules
│   ├── users/               # Utilisateurs, rôles, authentification
│   └── templates/           # Interfaces web (landing, login, admin, teacher, student)
├── mobile/                  # Application Flutter (provider, services, écrans)
├── docs/                    # Diagrammes et images
├── docker-compose.yml       # PostgreSQL + Redis + Django (Daphne)
├── requirements.txt         # Dépendances Python essentielles
└── .env.example             # Modèle de configuration (sans secret)
```

---

## Prérequis

- Python 3.13+ (Django 6.0.5)
- PostgreSQL (ou une base compatible accessible par `DATABASE_URL`, par exemple Neon)
- Redis (facultatif en local, utilisé par Django Channels en production)
- Flutter / Dart SDK 3.11+ pour l’application mobile
- Docker et Docker Compose pour un lancement conteneurisé

---

## Installation locale (backend + interface web)

Depuis la racine du dépôt, sous PowerShell :

```powershell
Copy-Item .env.example .env
# Éditer .env : DATABASE_URL, DJANGO_SECRET_KEY, DJANGO_DEBUG, SMTP...

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd backend
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

> `backend/requirements.txt` contient un environnement complet figé (pytest, Jupyter, outils de diagnostic, etc.) ; `requirements.txt` à la racine suffit pour exécuter l’application.

L’interface est alors disponible sur **http://localhost:8000**.

### Lancement avec Docker

```powershell
docker compose up --build
```

Le service `backend` applique les migrations puis démarre Daphne sur le port `8000`. PostgreSQL et Redis sont exposés sur `5432` et `6379`.

---

## Application mobile (Flutter)

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test

# Émulateur Android :
flutter run --dart-define=DEV_HOST=10.0.2.2

# Appareil physique sur le même réseau :
flutter run --dart-define=DEV_HOST=ADRESSE_IP_DU_PC

# Backend distant (production) :
flutter run --dart-define=API_BASE_URL=https://exemple.onrender.com/api/v1
```

Par défaut, l’application utilise `http://<DEV_HOST>:8000/api/v1`. Le schéma de deep link est `presenceqr://`.

**Dépannage Flutter (machine de développement Windows)** : si `flutter` échoue avec une erreur de moteur précompilé, définir la variable d’environnement suivante avant la commande :

```powershell
$env:FLUTTER_PREBUILT_ENGINE_VERSION = (Get-Content C:\flutter\bin\internal\engine.version)
```

---

## URLs utiles

| URL | Description |
|---|---|
| `/` | Page d’accueil |
| `/login/` | Connexion web |
| `/admin-ui/` | Tableau de bord administrateur |
| `/teacher/` | Espace enseignant |
| `/student/` | Espace étudiant |
| `/attend/` | Marquage de présence (lien QR / web) |
| `/health/` | Santé du service et de la base de données (JSON) |
| `/api/v1/` | Racine de l’API REST |
| `/api/docs/swagger/` | Documentation Swagger |
| `/admin/` | Administration Django intégrée |

L’authentification API se fait via `POST /api/v1/auth/login/` (email + mot de passe), puis envoi du jeton d’accès dans l’en-tête `Authorization: Bearer <token>`. Les jetons sont gérés par `djangorestframework-simplejwt`.

---

## Configuration (fichier `.env`)

| Variable | Rôle | Valeur par défaut / exemple |
|---|---|---|
| `DATABASE_URL` | Connexion PostgreSQL | `postgresql://postgres@127.0.0.1:5432/presenceqr_db` |
| `DJANGO_SECRET_KEY` | Clé secrète Django | à générer, ne jamais committer |
| `DJANGO_DEBUG` | Mode debug | `True` en développement, `False` en production |
| `EMAIL_HOST` / `EMAIL_PORT` | Serveur SMTP (Brevo) | `smtp-relay.brevo.com` / `587` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Identifiants SMTP | à renseigner |
| `DEFAULT_FROM_EMAIL` | Expéditeur des e-mails | `change-me@example.com` |
| `SITE_BASE_URL` | URL publique utilisée dans les QR codes | `http://172.30.251.9:8000` |
| `APP_DEEP_LINK_SCHEME` | Schéma d’ouverture de l’app mobile | `presenceqr` |
| `CORS_ALLOWED_ORIGINS` | Origines autorisées (production) | `http://localhost:3000 http://localhost:8000` |

Le fichier `.env` est ignoré par Git : ne jamais versionner de mot de passe, de clé API ou de jeton.

---

## Vérifications

```powershell
# Backend
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test

# Mobile
cd mobile
flutter analyze
flutter test
```

`flutter analyze` peut remonter des informations de dépréciation (`withOpacity`) sans empêcher la compilation : ce ne sont pas des erreurs bloquantes.

---

## Auteur

Projet PFE — Abderrahim Talibi, Master 1 SDIA, Université Moulay Ismaïl, Meknès (Maroc).
