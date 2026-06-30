@echo off
cd /d "%~dp0"
echo Demarrage de DataLens sur http://127.0.0.1:5000
"%~dp0venv\Scripts\python.exe" "%~dp0app.py"
pause
