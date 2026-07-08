@echo off
echo Starting Django with Daphne (ASGI server for WebSockets)...
cd /d "%~dp0"
venv\Scripts\python.exe -m daphne config.asgi:application --bind 0.0.0.0 --port 8000
