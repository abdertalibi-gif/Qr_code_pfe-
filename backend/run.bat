@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: Run Django server
python manage.py runserver --noreload 127.0.0.1:8000

pause
