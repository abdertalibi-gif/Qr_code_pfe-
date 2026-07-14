# Déploiement — QR Attendance System

## Architecture

```
┌──────────────────────────────┐
│  Flutter Mobile App           │
│  (étudiants, enseignants)     │
└──────────────┬───────────────┘
               │ HTTPS / WSS
               ▼
┌──────────────────────────────┐
│  Serveur Django               │
│  - Daphne (ASGI)              │
│  - DRF API                    │
│  - Templates admin (Django)   │
│  - WebSocket (Channels)       │
└──────────────┬───────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
┌──────────┐   ┌──────────────┐
│ PostgreSQL│   │  Redis (opt) │
│ (Neon)    │   │  (prod WS)   │
└──────────┘   └──────────────┘
```

## 1. Prérequis

- Python 3.12+
- PostgreSQL (ou utiliser Neon — déjà configuré dans `.env`)
- Node.js (optionnel, pour collectstatic)
- Un serveur Linux (Ubuntu 22.04 recommandé) ou un PaaS (Railway, Render, Heroku)

## 2. Backend — Déploiement

### 2.1 Option A — VPS (Ubuntu)

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx git redis-server

# Cloner le projet
git clone <votre-repo> attendance-system
cd attendance-system

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
pip install gunicorn channels-redis  # Redis pour prod WebSocket

# Aller dans le dossier backend
cd backend

# Variables d'environnement
cat > .env << EOF
DJANGO_SECRET_KEY="<generer-une-cle-aleatoire>"
DJANGO_DEBUG="False"
DATABASE_URL="postgresql://user:pass@host:5432/dbname?sslmode=require"
CORS_ALLOWED_ORIGINS="https://votredomaine.com https://api.votredomaine.com"
SITE_BASE_URL="https://votredomaine.com"
EOF

# Migrations et statiques
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# Tester
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

#### Fichier systemd — `/etc/systemd/system/attendance.service`

```ini
[Unit]
Description=QR Attendance Django App
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/attendance-system/backend
EnvironmentFile=/opt/attendance-system/backend/.env
ExecStart=/opt/attendance-system/venv/bin/daphne -b 127.0.0.1 -p 8000 config.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Nginx — `/etc/nginx/sites-available/attendance`

```nginx
server {
    listen 80;
    server_name votredomaine.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name votredomaine.com;

    ssl_certificate /etc/ssl/certs/...
    ssl_certificate_key /etc/ssl/private/...

    client_max_body_size 10M;

    location /static/ {
        alias /opt/attendance-system/backend/staticfiles/;
    }

    location /media/ {
        alias /opt/attendance-system/backend/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2.2 Option B — Railway (recommandé, facile)

1. Créer un compte sur [Railway](https://railway.app)
2. Connecter ton repo GitHub
3. Configurer les variables d'environnement :

| Variable | Valeur |
|---|---|
| `DJANGO_SECRET_KEY` | `<clé aléatoire>` |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_URL` | Provisionnée par Railway (PostgreSQL) |
| `CORS_ALLOWED_ORIGINS` | `https://ton-app.railway.app` |

4. `Procfile` à la racine :

```yaml
web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
release: cd backend && python manage.py migrate
```

5. `runtime.txt` :

```txt
python-3.12.9
```

### 2.3 Option C — Render

1. Créer un **Web Service** sur Render
2. Build command : `cd backend && pip install -r ../requirements.txt && python manage.py collectstatic --noinput`
3. Start command : `cd backend && daphne -b 0.0.0.0 -p $PORT config.asgi:application`
4. Ajouter un cron ou un service cron pour les tâches planifiées (si besoin)

## 3. Mobile Flutter

### Build APK / App Bundle

```bash
cd mobile

# Android APK
flutter build apk --release

# Android App Bundle (Play Store)
flutter build appbundle --release

# iOS (macOS uniquement)
flutter build ios --release
```

### Configuration

Dans `mobile/lib/config/env.dart` (ou fichier similaire), mettre à jour :

```dart
static const String apiBaseUrl = 'https://votredomaine.com/api/v1';
```

### Publication

- **Android** : Google Play Console
- **iOS** : App Store Connect

## 4. Sécurité — Checklist

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` générée (32+ caractères aléatoires)
- [ ] HTTPS activé (certificat SSL)
- [ ] `ALLOWED_HOSTS` restreint dans les settings
- [ ] Database URL avec `sslmode=require`
- [ ] Rate limiting actif (DRF throttle — déjà configuré)
- [ ] Redis (optionnel) pour Channels en production multi-process

## 5. Commandes utiles

```bash
# Générer une secret key
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Backup DB (PostgreSQL)
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d).sql

# Restore DB
psql "$DATABASE_URL" < backup_20260713.sql

# Voir les logs (systemd)
journalctl -u attendance.service -f

# Redémarrer
sudo systemctl restart attendance
```

## 6. Structure des dossiers (backend)

```
backend/
├── config/          # Settings, URLs, WSGI/ASGI
├── users/           # Authentification, profils
├── attendance/      # Gestion des séances/QR
├── courses/         # Cours, sessions
├── curriculum/      # Filières, semestres, modules
├── templates/       # Pages admin Django
├── scripts/         # Scripts utilitaires
├── media/           # Uploads (QR codes, imports)
├── staticfiles/     # Fichiers statiques (collectstatic)
├── manage.py
└── requirements.txt
```
