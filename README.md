# AttendQR — Smart QR Code Attendance Management System

<div align="center">

<img src="docs/images/attendqr-banner.svg" alt="AttendQR Premium Banner" width="100%" />

**Système intelligent de gestion des présences par code QR — Administration, Enseignants, Étudiants**

[![Python](https://img.shields.io/badge/Python-3.13-0D0D0D?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-DC143C?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django%20REST%20Framework-3.15-B5121B?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![Flutter](https://img.shields.io/badge/Flutter-3.11-0D0D0D?logo=flutter&logoColor=white)](https://flutter.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-DC143C?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/Authentication-JWT-B5121B?logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![Django Channels](https://img.shields.io/badge/WebSocket-Django%20Channels-0D0D0D?logo=channels&logoColor=white)](https://channels.readthedocs.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-B5121B?logo=docker&logoColor=white)](https://www.docker.com/)

[📖 Installation](#installation) · [🚀 Quick Start](#quick-start) · [📡 API Documentation](#api-documentation) · [🏗️ Deployment](#deployment)

</div>

---

## 📋 Table of Contents

- [About the Project](#about-the-project)
- [Visual Preview](#visual-preview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [Running the Project](#running-the-project)
- [API Documentation](#api-documentation)
- [Database Model](#database-model)
- [QR Code Workflow](#qr-code-workflow)
- [Security](#security)
- [Deployment](#deployment)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Author & Credits](#author--credits)

---

## About the Project

**AttendQR** is a complete QR-code based attendance management system for schools and universities. It enables administrators, teachers, and students to manage course sessions, generate QR attendance codes, and validate presence in real-time — via a Flutter mobile application and a Django web interface.

### Problem it solves

Manual attendance tracking is time-consuming, error-prone, and difficult to audit. AttendQR automates the process with:

- Unique QR codes generated per session
- Geolocation validation (50m geofence)
- Time-window control (active sessions only)
- Excel report exports

### Objectives

- Simplify attendance taking for teachers
- Provide students with fast mobile validation
- Give administrators a global view and actionable reports

### Key Benefits

| Benefit | Description |
|---------|-------------|
| ⚡ **Fast** | Presence validated in seconds via QR scan |
| 📍 **Secure** | Geofence and time-window controls |
| 📊 **Traceable** | Attendance history and Excel reports |
| 👥 **Multi-role** | Admin, Teacher, Student with dedicated permissions |
| 🔐 **Authenticated** | JWT access token (1h) + refresh token (7d) |

---

## Visual Preview

<div align="center">

<img src="docs/images/mockup-login.svg" alt="AttendQR Login Page" width="600" />

*Concept illustration based on the project's `login.html` template.*

</div>

<div align="center">

<img src="docs/images/mockup-admin.svg" alt="AttendQR Admin Dashboard" width="900" />

*Concept illustration based on the project's `admin_*.html` templates.*

</div>

<div align="center">

<img src="docs/images/mockup-teacher.svg" alt="AttendQR Teacher Form" width="600" />

*Concept illustration based on `session_form_screen.dart` in the mobile app.*

</div>

<div align="center">

<img src="docs/images/mockup-student.svg" alt="AttendQR Student Mobile" width="900" />

*Concept illustration based on the Flutter screens in the mobile app.*

</div>

> 💡 The visuals above are **concept illustrations** based on the project's templates and screens. They are not live screenshots of the running application.

---

## Key Features

### 🎓 Administrator

- User management (create, edit, delete)
- Class, filière, semester, and module management
- Teacher and student management
- Location management (blocks, rooms, amphitheaters)
- View all sessions and attendance records
- Excel report exports
- Global statistics dashboard

### 👨‍🏫 Teacher

- Create course sessions
- Select a class from assigned classes
- Generate and display session QR Code
- **Session location**: pre-filled automatically from the class, editable if needed (the original class configuration is never modified)
- Real-time attendance validation
- View session statistics
- Monthly report exports

### 📱 Student

- View timetable by semester
- Scan QR Code to validate presence
- Geolocation validation (50m geofence)
- Attendance history
- Instant confirmation

### 📱 QR Code Attendance

- Unique QR token generated per session (20 min default validity)
- QR displayed on teacher's screen
- Student scans via mobile app
- Geolocation and time-window controls
- Immediate attendance recording

### 📊 Reports & Analytics

- Global statistics (users, classes, teachers, sessions)
- Attendance reports per session
- Monthly reports for teachers
- Excel export

### 🔐 Security

- JWT authentication (SimpleJWT)
- Access token: 1 hour | Refresh token: 7 days
- Rate limiting (30 req/min anonymous, 120 req/min user)
- Role-Based Access Control (RBAC)
- Geofencing (50m radius)
- CSRF and CORS protection

---

## System Architecture

<div align="center">

<img src="docs/diagrams/architecture.svg" alt="AttendQR System Architecture" width="100%" />

*System architecture — components and data flows.*

</div>

| Layer | Technology | Role |
|-------|------------|------|
| **Client** | Flutter Mobile, Django Web Templates | UI, QR scan, dashboards |
| **API** | Django REST Framework | REST endpoints `/api/v1/`, JWT auth |
| **Backend** | Django 6.0 + Daphne (ASGI) | Business logic, live WebSocket |
| **Database** | PostgreSQL (Neon) | Users, classes, sessions, attendance |
| **Cache / WS** | Redis (optional prod) | Channel layer for WebSocket |

---

## Technology Stack

<div align="center">

<table>
  <tr>
    <td><b>Category</b></td>
    <td><b>Technology</b></td>
    <td><b>Version</b></td>
    <td><b>Usage</b></td>
  </tr>
  <tr>
    <td>Backend</td>
    <td>Python</td>
    <td>3.13</td>
    <td>Main language</td>
  </tr>
  <tr>
    <td>Web Framework</td>
    <td>Django</td>
    <td>6.0.5</td>
    <td>Application, ORM, templates</td>
  </tr>
  <tr>
    <td>API</td>
    <td>Django REST Framework</td>
    <td>3.15.2</td>
    <td>REST endpoints, serializers</td>
  </tr>
  <tr>
    <td>Authentication</td>
    <td>SimpleJWT</td>
    <td>5.3.1</td>
    <td>Access & refresh tokens</td>
  </tr>
  <tr>
    <td>Real-time</td>
    <td>Django Channels + Daphne</td>
    <td>4.1.0 / 4.1.2</td>
    <td>WebSocket, live sessions</td>
  </tr>
  <tr>
    <td>Database</td>
    <td>PostgreSQL</td>
    <td>15+ (Neon)</td>
    <td>Data storage</td>
  </tr>
  <tr>
    <td>Mobile</td>
    <td>Flutter (Dart)</td>
    <td>SDK 3.11.5</td>
    <td>Android/iOS app</td>
  </tr>
  <tr>
    <td>App Server</td>
    <td>Daphne / Gunicorn</td>
    <td>4.1.2 / 23.0.0</td>
    <td>ASGI / WSGI server</td>
  </tr>
  <tr>
    <td>Email</td>
    <td>Brevo SMTP</td>
    <td>—</td>
    <td>Password reset</td>
  </tr>
  <tr>
    <td>Containerization</td>
    <td>Docker + Docker Compose</td>
    <td>—</td>
    <td>PostgreSQL, Redis, Backend</td>
  </tr>
</table>

</div>

---

## Project Structure

```
attendance-system-QR/
├── backend/                          # Django application
│   ├── config/                       # Settings, URLs, WSGI/ASGI
│   ├── courses/                      # Sessions, courses
│   ├── users/                        # Users, classes, auth
│   ├── attendance/                   # Attendance management
│   ├── curriculum/                   # Filières, semesters, modules
│   ├── templates/                    # HTML templates (Admin, Teacher, Student)
│   ├── staticfiles/                  # Collected static files
│   ├── media/                        # Uploads (QR codes, reports)
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile                    # Backend Docker image
│   ├── manage.py                     # Django entry point
│   └── venv/                         # Local virtual environment
├── mobile/                           # Flutter application
│   ├── lib/
│   │   ├── constants/                # Constants, API config
│   │   ├── core/                     # RBAC, Router, Storage
│   │   ├── features/                 # Features (sessions, dashboard, etc.)
│   │   ├── models/                   # Data models (Classe, Session, etc.)
│   │   ├── providers/                # State management (Provider)
│   │   ├── repositories/             # Data access
│   │   ├── screens/                  # Screens (Login, Sessions, QR Scanner, etc.)
│   │   ├── services/                 # API services (Dio client, Auth, etc.)
│   │   ├── shared/                   # Shared widgets & utilities
│   │   └── main.dart                 # Flutter entry point
│   ├── pubspec.yaml                  # Flutter dependencies
│   ├── android/                      # Native Android project
│   └── ios/                          # Native iOS project
├── docs/
│   ├── images/                       # Visual assets (banner, logo, mockups)
│   └── diagrams/                     # Diagrams (architecture, workflow, ER)
├── docker-compose.yml                # Orchestration (PostgreSQL, Redis, Backend)
├── .env.example                      # Configuration template (no secrets)
├── .gitignore                        # Git ignored files
└── README.md                         # This document
```

---

## Installation

### Prerequisites

| Tool | Minimum Version |
|------|-----------------|
| Python | 3.12+ |
| pip | Latest |
| PostgreSQL | 15+ (or use Neon) |
| Flutter | SDK 3.11.5+ (for mobile) |
| Docker (optional) | 20.10+ |

### Clone the Repository

```bash
git clone https://github.com/abdertalibi-gif/Qr_code_pfe-.git
cd attendance-system-QR
```

---

## Environment Configuration

Create a `.env` file at the project root (based on `.env.example`):

```ini
# Database (PostgreSQL connection URL)
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require

# Django secret key (generate a unique value — do not reuse the default)
DJANGO_SECRET_KEY=change-me-with-a-random-50-char-string

# Debug mode (True only in development)
DJANGO_DEBUG=False

# Authorized hosts in production (space-separated)
ALLOWED_HOSTS=yourdomain.com api.yourdomain.com

# SMTP (Brevo for password reset emails)
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=change-me@example.com
EMAIL_HOST_PASSWORD=change-me
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Public site URL
SITE_BASE_URL=https://yourdomain.com

# Mobile app deep link scheme
APP_DEEP_LINK_SCHEME=presenceqr

# QR token validity (minutes)
QR_TOKEN_DEFAULT_EXPIRY_MINUTES=20

# Authorized CORS origins (space-separated)
CORS_ALLOWED_ORIGINS=https://yourdomain.com https://api.yourdomain.com
```

> ⚠️ **Security**: Never commit the `.env` file containing real secrets. The `.env.example` file is provided as a template.

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | Debug mode | `False` in production |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:pass@host:5432/db` |
| `SITE_BASE_URL` | Public API URL | `https://api.yourdomain.com` |
| `CORS_ALLOWED_ORIGINS` | Authorized CORS origins | `https://app.yourdomain.com` |

---

## Running the Project

### Backend (Django)

```bash
# Access the backend folder
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser (admin)
python manage.py createsuperuser

# Run development server
python manage.py runserver 127.0.0.1:8000

# Or with Daphne (ASGI for WebSocket)
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

### Mobile Application (Flutter)

```bash
cd mobile

# Install dependencies
flutter pub get

# Run in development (emulator or physical device)
flutter run

# Specify API URL if needed
flutter run --dart-define=API_BASE_URL=https://your-api.com/api/v1

# Build release APK
flutter build apk --release

# Build App Bundle (Play Store)
flutter build appbundle --release
```

### With Docker (optional)

```bash
# At the project root
docker-compose up -d

# This launches:
# - PostgreSQL (port 5432)
# - Redis (port 6379)
# - Backend Django (port 8000)
```

---

## API Documentation

The REST API is available under `/api/v1/` and documented via Swagger / ReDoc.

### Authentication

All protected endpoints require the header `Authorization: Bearer <access_token>`.

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/api/v1/auth/login/` | User login | No |
| `POST` | `/api/v1/auth/token/refresh/` | Refresh access token | No (refresh token) |
| `GET` | `/api/v1/users/` | List users | Yes (Admin) |
| `GET` | `/api/v1/classes/` | List classes | Yes |
| `GET` | `/api/v1/students/` | List students | Yes |
| `POST` | `/api/v1/sessions/` | Create session | Yes |
| `GET` | `/api/v1/sessions/` | List sessions | Yes |
| `GET` | `/api/v1/sessions/{id}/` | Session detail | Yes |
| `GET` | `/api/v1/dashboard/counts/` | Dashboard statistics | Yes |
| `GET` | `/api/v1/blocks/` | List blocks | Yes |
| `GET` | `/api/v1/rooms/` | List rooms | Yes |
| `GET` | `/api/v1/amphitheaters/` | List amphitheaters | Yes |
| `GET` | `/api/v1/teachers/` | List teachers | Yes |
| `GET` | `/api/v1/departments/` | List departments | Yes |

### Swagger UI

Once the server is running:
- Swagger: `http://localhost:8000/api/docs/swagger/`
- ReDoc: `http://localhost:8000/api/docs/redoc/`
- Schema JSON: `http://localhost:8000/api/docs/swagger.json`

### Web Pages (served by Django)

| Page | URL | Role |
|------|-----|------|
| Home | `/` | Public landing page |
| Login | `/login/` | Authentication |
| Admin | `/admin-ui/` | Admin Dashboard |
| Teacher | `/teacher/` | Teacher Space |
| Student | `/student/` | Student Space |
| QR Validate | `/attend/` | QR Validation Page |
| Admin: Classes | `/admin/classes/` | Class Management |
| Admin: Sessions | `/admin/sessions/` | Session Management |
| Admin: Users | `/admin/users/` | User Management |

---

## Database Model

<div align="center">

<img src="docs/diagrams/database-er.svg" alt="Database ER Diagram" width="100%" />

*Entity-Relationship diagram based on the project's Django models.*

</div>

| Entity | Key Attributes | Relations |
|--------|---------------|-----------|
| **User** | id, email, full_name, role, department_id | Teaches sessions, belongs to department |
| **Classe** | id, name, code, niveau, filiere_id, semestre_id, module_id | Has sessions, linked to filière |
| **Session** | id, subject, classe_id, teacher_id, location_type, block_id, room_id, amphitheater_id, date, start_time, end_time | Belongs to class and teacher, has a location |
| **Filiere** | id, name, semestre_id, department_id | Contains classes and modules |
| **Semestre** | id, name | Linked to filières |
| **Module** | id, name, filiere_id | Linked to classes and sessions |
| **Block** | id, name | Contains rooms |
| **Room** | id, name, block_id | Belongs to a block |
| **Amphitheater** | id, name | Session location |
| **Department** | id, name | Contains users and filières |

---

## QR Code Workflow

<div align="center">

<img src="docs/diagrams/qr-workflow.svg" alt="QR Code Attendance Workflow" width="100%" />

*Complete flow from session creation to attendance validation.*

</div>

### Workflow Steps

1. **Session creation**: The teacher selects a class, module, date, and time. The server generates a unique QR token (20 min default validity).
2. **QR display**: The QR code is displayed on the teacher's screen or projected in class.
3. **Student scan**: The student scans the QR via the mobile app. Geolocation and device fingerprint are captured.
4. **Server validation**: The server checks token validity, expiration, geofence (50m), and session time window.
5. **Confirmation**: The student receives immediate confirmation. The teacher sees attendance in real-time. An Excel report is available for the admin.

### Workflow Security

- ✅ Signed JWT token
- ✅ QR expiration (20 min configurable)
- ✅ Geofence (50m radius around session location)
- ✅ Time-window control (active sessions only)
- ✅ Device fingerprint to prevent duplicates

---

## Security

The following security measures are implemented in the project:

| Measure | Detail |
|---------|--------|
| **JWT Authentication** | Access token (1h) + Refresh token (7d) via SimpleJWT |
| **Rate Limiting** | 30 req/min (anonymous), 120 req/min (user), 10 req/min (presence validation) |
| **Access Control** | Role-based permissions (Admin / Teacher / Student) |
| **Geofencing** | Presence validated only within 50m of session location |
| **Time Window** | Presence validated only during active session |
| **CSRF Protection** | Django CSRF middleware enabled |
| **CORS** | Origins configured via `CORS_ALLOWED_ORIGINS` |
| **Secure Cookies** | `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` in production (`DEBUG=False`) |
| **HTTPS Redirect** | `SECURE_SSL_REDIRECT` enabled in production |

> ⚠️ **Important**: A `.env` file containing secrets was identified in the Git history. Before any production deployment, revoke the exposed credentials (Neon database password, Brevo SMTP password) and generate new keys.

---

## Deployment

AttendQR is designed to be deployed on a platform supporting persistent processes (Django + Daphne ASGI + WebSocket).

> ⚠️ **Vercel is not recommended** for this project because it is serverless and does not natively support persistent processes, persistent WebSocket, or Daphne/ASGI in continuous mode.

### Recommended: Railway or Render

#### Railway

1. Connect your GitHub repository to [Railway](https://railway.app)
2. Add a managed PostgreSQL database on Railway
3. Add Redis (for WebSocket in multi-process production)
4. Configure environment variables:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG=False`
   - `DATABASE_URL` (provided by Railway PostgreSQL)
   - `CORS_ALLOWED_ORIGINS=https://your-domain.com`
   - `SITE_BASE_URL=https://your-domain.com`
5. Build command: `cd backend && pip install -r requirements.txt && python manage.py collectstatic --noinput`
6. Start command: `cd backend && daphne -b 0.0.0.0 -p $PORT config.asgi:application`

#### Render

1. Create a **Web Service** on [Render](https://render.com)
2. Add a managed PostgreSQL database
3. Build command: `cd backend && pip install -r requirements.txt && python manage.py collectstatic --noinput`
4. Start command: `cd backend && daphne -b 0.0.0.0 -p $PORT config.asgi:application`

### VPS (full control)

See the `DEPLOY.md` file for the complete procedure with Nginx, systemd, and SSL certificate.

### Deployment Checklist

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` generated (32+ random characters)
- [ ] `ALLOWED_HOSTS` restricted to production domains
- [ ] `DATABASE_URL` with `sslmode=require`
- [ ] HTTPS enabled (SSL certificate)
- [ ] Redis configured for Channels (multi-process production)
- [ ] `.env` file not committed to Git
- [ ] Exposed credentials in Git history revoked

---

## Testing

### Backend (Django)

```bash
cd backend

# Run all tests
python manage.py test

# Test a specific app
python manage.py test users
python manage.py test courses
python manage.py test attendance
python manage.py test curriculum

# Check the project
python manage.py check

# Check migrations
python manage.py makemigrations --check --dry-run
```

### Mobile (Flutter)

```bash
cd mobile

# Analyze code
flutter analyze

# Run unit and widget tests
flutter test

# Check dependencies
flutter pub outdated
```

---

## Roadmap

### ✅ Implemented

- Multi-role authentication (Admin, Teacher, Student) with JWT
- Class, filière, semester, module management
- Session creation and management
- QR Code generation and scanning
- Geofence and time-window control
- Admin, Teacher, Student dashboards
- Excel report exports
- WebSocket for live attendance
- REST API documented (Swagger/ReDoc)
- Flutter mobile app (Android/iOS)

### 🚧 In Progress / Future

- Push notifications for sessions
- Advanced analytics dashboard (charts)
- Google Calendar / Outlook integration
- PDF report exports
- Multi-language (FR/EN)
- PWA app for validation without mobile installation

---

## Author & Credits

<div align="center">

**AttendQR — Smart QR Code Attendance Management System**

Developed with ❤️ for academic attendance management.

[🔗 View on GitHub](https://github.com/abdertalibi-gif/Qr_code_pfe-.git)

</div>

---

<div align="center">

<sub>Documentation generated for the GitHub repository. Visual illustrations are concept representations based on the project's real templates and screens.</sub>

</div>
