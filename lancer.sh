#!/usr/bin/env bash
# ============================================================
#  Génome & COVID — lancement de l'application (Linux/macOS)
#  Nécessite Docker Engine + le plugin Compose v2
#  (https://docs.docker.com/engine/install/)
# ============================================================
set -e
cd "$(dirname "$0")"

echo "Construction / démarrage du conteneur…"
docker compose up -d --build

echo
echo "L'application démarre sur http://localhost:8080"
sleep 3

# ouvrir le navigateur si possible (X11 / Wayland / macOS)
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://localhost:8080 >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open http://localhost:8080 || true
fi
