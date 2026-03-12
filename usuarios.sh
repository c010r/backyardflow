#!/bin/bash
# BackyardFlow — Gestión de usuarios desde terminal (Linux/Ubuntu)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
    echo "[ERROR] Archivo .env no encontrado."
    exit 1
fi

# Cargar variables de entorno (maneja valores entre comillas simples)
while IFS='=' read -r key val; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    val="${val#\'}" ; val="${val%\'}"   # quitar comillas simples
    val="${val#\"}" ; val="${val%\"}"   # quitar comillas dobles
    export "$key=$val"
done < .env

# Activar venv
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "[ERROR] Entorno virtual no encontrado. Ejecutá deploy.sh primero."
    exit 1
fi

python manage.py gestionar_usuarios
