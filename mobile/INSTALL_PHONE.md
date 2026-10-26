# Installer et lancer l'application mobile sur le téléphone

## Option A — USB, sans Wi-Fi (recommandée pour tester maintenant)

Le téléphone est connecté en USB au PC et le débogage USB est déjà actif.

### 1. Lancer le backend Django sur le PC

Dans un terminal :

```powershell
cd "C:\Users\Abde\Desktop\attendance-system-QR (7)\attendance-system-QR\backend"
$env:PYTHONIOENCODING='utf-8'
python manage.py runserver 0.0.0.0:8010
```

Le serveur doit rester ouvert pendant l'utilisation de l'application.

### 2. Créer le tunnel USB

Dans un deuxième terminal :

```powershell
$adb = "$env:LOCALAPPDATA\Android\sdk\platform-tools\adb.exe"
& $adb reverse tcp:8000 tcp:8010
& $adb devices
```

`adb devices` doit afficher le téléphone avec l'état `device`.

### 3. Installer et lancer l'application

Le plus simple :

```text
Double-cliquer sur mobile\run_on_phone.bat
```

Ou en PowerShell :

```powershell
cd "C:\Users\Abde\Desktop\attendance-system-QR (7)\attendance-system-QR\mobile"
$env:PATH = 'C:\Program Files\Git\cmd;' + $env:PATH
flutter run -d R8YY608FJ8M --dart-define=DEV_HOST=127.0.0.1
```

L'application utilise alors :

```text
http://127.0.0.1:8000/api/v1
```

sur le téléphone, redirigé par USB vers le backend du PC sur le port `8010`.

### 4. Première utilisation

1. Ouvrir l'application **AttendQR**.
2. Se connecter avec un compte existant.
3. Accepter la permission caméra au premier scan.
4. Accepter la permission localisation si l'application la demande.
5. Garder le câble USB branché et le backend démarré.

> Sans câble USB, cette configuration ne fonctionne plus. Utiliser l'option B.

---

## Option B — Wi-Fi, application autonome

### 1. Mettre le téléphone sur le même Wi-Fi que le PC

Vérifier l'adresse IP du PC :

```powershell
ipconfig
```

Ici l'adresse Wi-Fi du PC est `192.168.31.91`.

### 2. Rendre le backend accessible sur le réseau

```powershell
cd "C:\Users\Abde\Desktop\attendance-system-QR (7)\attendance-system-QR\backend"
$env:PYTHONIOENCODING='utf-8'
python manage.py runserver 0.0.0.0:8010
```

Autoriser Python dans le pare-feu Windows si demandé.

Tester depuis le navigateur du téléphone :

```text
http://192.168.31.91:8010/login/
```

Si cette page ne s'ouvre pas, le téléphone et le PC ne sont pas sur le même réseau ou le pare-feu bloque le port.

### 3. Compiler l'APK avec la bonne adresse API

```powershell
cd "C:\Users\Abde\Desktop\attendance-system-QR (7)\attendance-system-QR\mobile"
$env:PATH = 'C:\Program Files\Git\cmd;' + $env:PATH
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.31.91:8010/api/v1
```

APK généré :

```text
mobile\build\app\outputs\flutter-apk\app-release.apk
```

### 4. Installer l'APK

Téléphone branché en USB :

```powershell
$adb = "$env:LOCALAPPDATA\Android\sdk\platform-tools\adb.exe"
& $adb install -r "build\app\outputs\flutter-apk\app-release.apk"
```

Ou copier l'APK sur le téléphone et l'ouvrir pour l'installer manuellement.

### 5. Lancer l'application

```powershell
& $adb shell am start -n com.pfeqr.attendance_app/.MainActivity
```

L'application peut ensuite être ouverte normalement depuis le tiroir d'applications, sous le nom **AttendQR**.

---

## Option C — Backend déployé en HTTPS (production)

Si le backend est déployé (Render, Railway, VPS, etc.) :

```powershell
flutter build apk --release --dart-define=API_BASE_URL=https://VOTRE-BACKEND/api/v1
```

C'est la configuration à utiliser pour une application réellement autonome, utilisable hors du réseau local. Le HTTPS est également nécessaire pour la géolocalisation web et recommandé pour l'application mobile.

---

## Dépannage

### `flutter` affiche `Unable to determine engine version`

Le `git` du PATH est cassé. Toujours préfixer le PATH :

```powershell
$env:PATH = 'C:\Program Files\Git\cmd;' + $env:PATH
```

### `adb` n'est pas reconnu

Utiliser le chemin complet :

```powershell
$adb = "$env:LOCALAPPDATA\Android\sdk\platform-tools\adb.exe"
& $adb devices
```

### Le téléphone n'apparaît pas dans `adb devices`

- Activer le mode développeur.
- Activer le débogage USB.
- Accepter la demande d'autorisation USB sur le téléphone.
- Changer de câble USB si nécessaire.

### L'application affiche une erreur réseau

- Vérifier que le backend tourne.
- Vérifier `adb reverse --list`.
- En Wi-Fi, tester l'URL dans le navigateur du téléphone.
- Vérifier que l'APK a bien été compilé avec la bonne `API_BASE_URL`.
