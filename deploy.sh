#!/usr/bin/env bash
# ============================================================
#  BackyardFlow POS — Deploy Ubuntu
#  Uso: sudo bash deploy.sh
#  Clona el repo, lo copia a /var/www/backyardflow y configura
#  nginx + gunicorn + systemd
# ============================================================
set -euo pipefail

# ── Colores ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${CYAN}[→]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗] $*${NC}"; exit 1; }
sep()  { echo -e "\n${BOLD}────────────────────────────────────────${NC}"; }

clear
echo -e "${BOLD}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║      BackyardFlow POS — Deploy Ubuntu            ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Verificaciones previas ────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Ejecutar como root: sudo bash deploy.sh"
command -v lsb_release &>/dev/null || err "Este script requiere Ubuntu"
UBUNTU_VER=$(lsb_release -rs)
ok "Ubuntu $UBUNTU_VER detectado"

# Directorio donde está el script (origen del repo clonado)
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Directorio destino final (donde nginx sirve el sistema)
DEPLOY_DIR="/var/www/backyardflow"

REAL_USER="${SUDO_USER:-$(whoami)}"
VENV="$DEPLOY_DIR/.venv"
SERVICE_NAME="backyardflow"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 1 — Dependencias del sistema                       ║
# ╚══════════════════════════════════════════════════════════╝
sep
info "Instalando dependencias del sistema..."

apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    nginx curl build-essential libpq-dev \
    git ufw rsync

ok "Dependencias instaladas"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 2 — Copiar proyecto a /var/www/backyardflow         ║
# ╚══════════════════════════════════════════════════════════╝
sep
info "Copiando proyecto a $DEPLOY_DIR ..."

mkdir -p "$DEPLOY_DIR"

# rsync: copia todos los archivos excepto venv, db, media y .env
rsync -a --delete \
    --exclude='.venv/' \
    --exclude='venv/' \
    --exclude='db.sqlite3' \
    --exclude='media/' \
    --exclude='staticfiles/' \
    --exclude='logs/' \
    --exclude='.env' \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    "$SOURCE_DIR/" "$DEPLOY_DIR/"

# Crear carpetas necesarias si no existen
mkdir -p "$DEPLOY_DIR/media" "$DEPLOY_DIR/logs" "$DEPLOY_DIR/staticfiles"

ok "Archivos copiados a $DEPLOY_DIR"
cd "$DEPLOY_DIR"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 3 — Entorno virtual Python                         ║
# ╚══════════════════════════════════════════════════════════╝
sep
if [[ ! -d "$VENV" ]]; then
    info "Creando entorno virtual..."
    python3 -m venv "$VENV"
fi
ok "Entorno virtual: $VENV"

info "Instalando dependencias Python..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$DEPLOY_DIR/requirements.txt"
"$VENV/bin/pip" install -q gunicorn whitenoise
ok "Paquetes Python instalados"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 4 — Configuración (.env)                           ║
# ╚══════════════════════════════════════════════════════════╝
sep
if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
    echo -e "\n${BOLD}  Configuración inicial del sistema${NC}\n"

    # ── Servidor ──
    read -rp "  Dominio o IP del servidor (ej: milocal.com o 192.168.1.10): " DOMAIN
    DOMAIN="${DOMAIN:-localhost}"

    # ── Local ──
    echo
    read -rp "  Nombre del local [BackyardFlow POS]: " RESTAURANT_NAME
    RESTAURANT_NAME="${RESTAURANT_NAME:-BackyardFlow POS}"
    read -rp "  Dirección: " RESTAURANT_ADDRESS
    read -rp "  Teléfono: " RESTAURANT_PHONE
    read -rp "  Símbolo de moneda [\$]: " CURRENCY_SYMBOL
    CURRENCY_SYMBOL="${CURRENCY_SYMBOL:-\$}"
    read -rp "  IVA % [0]: " TAX_PERCENT
    TAX_PERCENT="${TAX_PERCENT:-0}"

    # ── Admin ──
    echo
    echo -e "  ${BOLD}Cuenta de administrador${NC}"
    read -rp "  Usuario [admin]: " ADMIN_USERNAME
    ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
    read -rp "  Email [admin@local.com]: " ADMIN_EMAIL
    ADMIN_EMAIL="${ADMIN_EMAIL:-admin@local.com}"
    while true; do
        read -rsp "  Contraseña: " ADMIN_PASSWORD; echo
        [[ ${#ADMIN_PASSWORD} -ge 8 ]] && break
        warn "Mínimo 8 caracteres"
    done

    # ── Base de datos ──
    echo
    read -rp "  ¿Usar PostgreSQL? (s/n) [n]: " USE_PG
    if [[ "${USE_PG,,}" == "s" ]]; then
        apt-get install -y -qq postgresql postgresql-contrib
        "$VENV/bin/pip" install -q psycopg2-binary

        DB_NAME="backyarddb"
        DB_USER="backyarduser"
        DB_PASSWORD='Backyard$2026'

        info "Configurando PostgreSQL..."
        sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" 2>/dev/null || \
            warn "El usuario ${DB_USER} ya existe — se continúa"
        sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null || \
            warn "La base de datos ${DB_NAME} ya existe — se continúa"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" 2>/dev/null || true
        sudo -u postgres psql -c "ALTER USER ${DB_USER} CREATEDB;" 2>/dev/null || true
        ok "PostgreSQL: base de datos '${DB_NAME}', usuario '${DB_USER}'"

        DB_ENGINE="django.db.backends.postgresql"
        DB_HOST="localhost"
        DB_PORT="5432"
    else
        DB_ENGINE="django.db.backends.sqlite3"
        DB_NAME="db.sqlite3"
        DB_USER=""; DB_PASSWORD=""; DB_HOST=""; DB_PORT=""
    fi

    # Generar SECRET_KEY
    SECRET_KEY=$("$VENV/bin/python" -c "import secrets; print(secrets.token_urlsafe(50))")

    cat > "$DEPLOY_DIR/.env" <<EOF
# BackyardFlow POS — Configuración
SECRET_KEY=${SECRET_KEY}
DEBUG=False
DOMAIN=${DOMAIN}
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},localhost,127.0.0.1

DB_ENGINE=${DB_ENGINE}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER:-}
DB_PASSWORD='${DB_PASSWORD:-}'
DB_HOST=${DB_HOST:-}
DB_PORT=${DB_PORT:-}

TIME_ZONE=America/Argentina/Buenos_Aires

ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

RESTAURANT_NAME=${RESTAURANT_NAME}
RESTAURANT_ADDRESS=${RESTAURANT_ADDRESS:-}
RESTAURANT_PHONE=${RESTAURANT_PHONE:-}
CURRENCY_SYMBOL=${CURRENCY_SYMBOL}
TAX_PERCENT=${TAX_PERCENT}
EOF
    chmod 640 "$DEPLOY_DIR/.env"
    ok ".env creado en $DEPLOY_DIR"
else
    ok ".env existente — usando configuración guardada"
fi

# Cargar variables (maneja valores con comillas simples)
while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" == \#* ]] && continue
    value="${value#\'}" ; value="${value%\'}"
    value="${value#\"}" ; value="${value%\"}"
    export "$key=$value"
done < "$DEPLOY_DIR/.env"

# DOMAIN: tomar del .env o derivar del primer valor de ALLOWED_HOSTS
if [[ -z "${DOMAIN:-}" ]]; then
    DOMAIN=$(echo "${ALLOWED_HOSTS:-localhost}" | cut -d',' -f1)
fi
export DOMAIN

export DJANGO_SETTINGS_MODULE="backyardflow.settings_prod"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 5 — Base de datos                                  ║
# ╚══════════════════════════════════════════════════════════╝
sep
info "Ejecutando migraciones..."
cd "$DEPLOY_DIR"
"$VENV/bin/python" manage.py migrate --run-syncdb
ok "Base de datos lista"

info "Configurando usuario administrador..."
"$VENV/bin/python" manage.py shell -c "
from django.contrib.auth.models import User
import os
u = os.environ.get('ADMIN_USERNAME', 'admin')
p = os.environ.get('ADMIN_PASSWORD', 'admin123')
e = os.environ.get('ADMIN_EMAIL', '')
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, e, p)
    print(f'  → Creado: {u}')
else:
    user = User.objects.get(username=u)
    user.set_password(p)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f'  → Actualizado: {u}')
"
ok "Usuario administrador listo"

info "Configurando datos del local..."
"$VENV/bin/python" manage.py shell -c "
from config.models import SystemSettings
from decimal import Decimal
import os
s = SystemSettings.get()
s.restaurant_name = os.environ.get('RESTAURANT_NAME', s.restaurant_name)
s.address         = os.environ.get('RESTAURANT_ADDRESS', s.address)
s.phone           = os.environ.get('RESTAURANT_PHONE', s.phone)
s.currency_symbol = os.environ.get('CURRENCY_SYMBOL', s.currency_symbol)
try:
    s.tax_percent = Decimal(os.environ.get('TAX_PERCENT', '0'))
except Exception:
    pass
s.save()
print(f'  → Local: {s.restaurant_name}')
"
ok "Datos del local guardados"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 6 — Archivos estáticos                             ║
# ╚══════════════════════════════════════════════════════════╝
sep
info "Recolectando archivos estáticos en $DEPLOY_DIR/staticfiles/ ..."
"$VENV/bin/python" manage.py collectstatic --noinput -v 0
ok "Archivos estáticos listos"

# Permisos finales
chown -R www-data:www-data "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"
chmod 640 "$DEPLOY_DIR/.env"
chmod 775 "$DEPLOY_DIR/media" "$DEPLOY_DIR/logs"
ok "Permisos configurados (www-data)"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 7 — Servicio systemd (Gunicorn)                    ║
# ╚══════════════════════════════════════════════════════════╝
sep
info "Creando servicio systemd..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=BackyardFlow POS (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=${DEPLOY_DIR}
EnvironmentFile=${DEPLOY_DIR}/.env
Environment="DJANGO_SETTINGS_MODULE=backyardflow.settings_prod"

# systemd crea /run/backyardflow/ con permisos correctos automáticamente
RuntimeDirectory=${SERVICE_NAME}
RuntimeDirectoryMode=0775

ExecStart=${VENV}/bin/gunicorn \\
    --workers 3 \\
    --bind unix:/run/${SERVICE_NAME}/gunicorn.sock \\
    --umask 007 \\
    --timeout 120 \\
    --access-logfile ${DEPLOY_DIR}/logs/access.log \\
    --error-logfile ${DEPLOY_DIR}/logs/error.log \\
    backyardflow.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5s
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

# Asegurar que nginx (www-data) puede leer el socket
usermod -aG www-data www-data 2>/dev/null || true

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

# Esperar hasta 10s a que el socket aparezca
SOCKET_PATH="/run/${SERVICE_NAME}/gunicorn.sock"
for i in {1..10}; do
    sleep 1
    if [[ -S "$SOCKET_PATH" ]]; then break; fi
done

if systemctl is-active --quiet "${SERVICE_NAME}" && [[ -S "$SOCKET_PATH" ]]; then
    ok "Servicio $SERVICE_NAME activo — socket: $SOCKET_PATH"
else
    echo
    warn "El servicio no arrancó correctamente. Diagnóstico:"
    systemctl status "${SERVICE_NAME}" --no-pager -l || true
    echo
    journalctl -u "${SERVICE_NAME}" -n 20 --no-pager || true
    err "Corregir errores arriba y volver a ejecutar deploy.sh"
fi

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 8 — nginx                                          ║
# ╚══════════════════════════════════════════════════════════╝
sep
info "Configurando nginx para servir desde $DEPLOY_DIR ..."

# server_name: incluir www. solo si es dominio raíz
_DOT_COUNT=$(echo "$DOMAIN" | tr -cd '.' | wc -c)
if [[ "$_DOT_COUNT" -ge 2 ]]; then
    NGINX_SERVER_NAME="$DOMAIN"
else
    NGINX_SERVER_NAME="$DOMAIN www.$DOMAIN"
fi

cat > "/etc/nginx/sites-available/${SERVICE_NAME}" <<EOF
server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    client_max_body_size 20M;

    access_log ${DEPLOY_DIR}/logs/nginx_access.log;
    error_log  ${DEPLOY_DIR}/logs/nginx_error.log;

    # Archivos estáticos — servidos directo por nginx (sin pasar por Django)
    location /static/ {
        alias ${DEPLOY_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }

    # Archivos subidos por usuarios
    location /media/ {
        alias ${DEPLOY_DIR}/media/;
        expires 7d;
    }

    # Todo lo demás → Gunicorn → Django
    location / {
        proxy_pass          http://unix:/run/${SERVICE_NAME}/gunicorn.sock;
        proxy_set_header    Host \$host;
        proxy_set_header    X-Real-IP \$remote_addr;
        proxy_set_header    X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto \$scheme;
        proxy_read_timeout  300;
        proxy_connect_timeout 60;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}" \
       "/etc/nginx/sites-enabled/${SERVICE_NAME}"
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
ok "nginx configurado — sirviendo desde $DEPLOY_DIR"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 9 — Firewall                                       ║
# ╚══════════════════════════════════════════════════════════╝
sep
info "Configurando firewall UFW..."
ufw allow OpenSSH >/dev/null
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null
ok "Firewall activo (SSH + HTTP/HTTPS permitidos)"

# ╔══════════════════════════════════════════════════════════╗
# ║  PASO 10 — SSL con Let's Encrypt (opcional)              ║
# ╚══════════════════════════════════════════════════════════╝
sep
if [[ "$DOMAIN" != "localhost" && "$DOMAIN" != "127.0.0.1" ]] && \
   [[ "$DOMAIN" =~ \. ]]; then
    read -rp "  ¿Instalar certificado SSL gratuito (Let's Encrypt)? (s/n) [n]: " INSTALL_SSL
    if [[ "${INSTALL_SSL,,}" == "s" ]]; then
        apt-get install -y -qq certbot python3-certbot-nginx

        # Contar puntos: si el dominio tiene 2+ puntos es un subdominio (ej: app.foo.com)
        # En ese caso NO agregar www. porque no existe en DNS
        DOT_COUNT=$(echo "$DOMAIN" | tr -cd '.' | wc -c)
        if [[ "$DOT_COUNT" -ge 2 ]]; then
            # Subdominio: solo pedir certificado para el dominio exacto
            CERTBOT_DOMAINS="-d $DOMAIN"
            info "Subdominio detectado — SSL solo para: $DOMAIN"
        else
            # Dominio raíz (ej: milocal.com): incluir www.
            CERTBOT_DOMAINS="-d $DOMAIN -d www.$DOMAIN"
            info "Dominio raíz — SSL para: $DOMAIN y www.$DOMAIN"
        fi

        certbot --nginx \
            $CERTBOT_DOMAINS \
            --non-interactive --agree-tos \
            -m "$ADMIN_EMAIL" \
            --redirect && ok "SSL instalado — HTTPS activo" \
            || warn "SSL falló. Verificar que el dominio apunte a este servidor."
    fi
fi

# ╔══════════════════════════════════════════════════════════╗
# ║  RESUMEN FINAL                                           ║
# ╚══════════════════════════════════════════════════════════╝
echo
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  DEPLOY COMPLETADO${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo
echo -e "  ${BOLD}Directorio:${NC}  $DEPLOY_DIR"
echo -e "  ${BOLD}URL:${NC}         http://${DOMAIN}"
echo -e "  ${BOLD}Usuario:${NC}     ${ADMIN_USERNAME}"
echo -e "  ${BOLD}Estáticos:${NC}   $DEPLOY_DIR/staticfiles/  (nginx directo)"
echo -e "  ${BOLD}Media:${NC}       $DEPLOY_DIR/media/         (nginx directo)"
echo -e "  ${BOLD}Logs:${NC}        $DEPLOY_DIR/logs/"
echo
echo -e "  ${BOLD}Comandos útiles:${NC}"
echo -e "    ${CYAN}systemctl status ${SERVICE_NAME}${NC}         # estado"
echo -e "    ${CYAN}journalctl -u ${SERVICE_NAME} -f${NC}          # logs en vivo"
echo -e "    ${CYAN}systemctl restart ${SERVICE_NAME}${NC}        # reiniciar app"
echo -e "    ${CYAN}systemctl reload nginx${NC}                   # recargar nginx"
echo
echo -e "  ${BOLD}Para actualizar el sistema:${NC}"
echo -e "    ${CYAN}cd $SOURCE_DIR && git pull${NC}"
echo -e "    ${CYAN}sudo bash deploy.sh${NC}   # re-copia y reinicia todo"
echo
