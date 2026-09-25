@echo off
rem ============================================================
rem  Genome & COVID - lancement de l'application
rem  Necessite Docker Desktop (https://www.docker.com/products/docker-desktop/)
rem ============================================================
cd /d "%~dp0"

echo Construction / demarrage du conteneur...
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo ERREUR : Docker ne semble pas disponible.
  echo Verifiez que Docker Desktop est installe et demarre.
  pause
  exit /b 1
)

echo.
echo L'application demarre sur http://localhost:8080
timeout /t 3 /nobreak >nul
start http://localhost:8080
