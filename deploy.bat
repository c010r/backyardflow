@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title BackyardFlow POS — Deploy Windows

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║          BackyardFlow POS — Setup y Deploy           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ── Verificar Python ──────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instalar desde https://python.org
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo [OK] %PY_VER%

:: ── Directorio del script ─────────────────────────────────
cd /d "%~dp0"
echo [OK] Directorio: %CD%

:: ── Entorno virtual ───────────────────────────────────────
if not exist ".venv\" (
    echo [INFO] Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 ( echo [ERROR] No se pudo crear el venv & pause & exit /b 1 )
    echo [OK] Entorno virtual creado
) else (
    echo [OK] Entorno virtual existente
)

:: ── Activar venv ──────────────────────────────────────────
call .venv\Scripts\activate.bat
if errorlevel 1 ( echo [ERROR] No se pudo activar el venv & pause & exit /b 1 )
echo [OK] Entorno virtual activado

:: ── Instalar dependencias ─────────────────────────────────
echo.
echo [INFO] Instalando/actualizando dependencias...
pip install -q --upgrade pip
pip install -q -r requirements.txt
if errorlevel 1 ( echo [ERROR] Fallo la instalacion de dependencias & pause & exit /b 1 )
echo [OK] Dependencias instaladas

:: ── Archivo .env ──────────────────────────────────────────
if not exist ".env" (
    echo.
    echo  ══════════════════════════════════════════════════════
    echo   CONFIGURACION INICIAL
    echo  ══════════════════════════════════════════════════════
    echo.

    set /p RESTAURANT_NAME="  Nombre del local [BackyardFlow POS]: "
    if "!RESTAURANT_NAME!"=="" set RESTAURANT_NAME=BackyardFlow POS

    set /p RESTAURANT_ADDRESS="  Direccion: "
    set /p RESTAURANT_PHONE="  Telefono: "
    set /p CURRENCY_SYMBOL="  Simbolo de moneda [$]: "
    if "!CURRENCY_SYMBOL!"=="" set CURRENCY_SYMBOL=$

    set /p TAX_PERCENT="  IVA %% [0]: "
    if "!TAX_PERCENT!"=="" set TAX_PERCENT=0

    echo.
    echo   -- Cuenta de administrador --
    set /p ADMIN_USERNAME="  Usuario admin [admin]: "
    if "!ADMIN_USERNAME!"=="" set ADMIN_USERNAME=admin

    set /p ADMIN_EMAIL="  Email admin [admin@local.com]: "
    if "!ADMIN_EMAIL!"=="" set ADMIN_EMAIL=admin@local.com

    :ask_pass
    set /p ADMIN_PASSWORD="  Contrasena admin: "
    if "!ADMIN_PASSWORD!"=="" ( echo  [!] La contrasena no puede estar vacia & goto ask_pass )

    :: Generar SECRET_KEY
    for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(50))"') do set SECRET_KEY=%%i

    :: Escribir .env
    (
        echo SECRET_KEY=!SECRET_KEY!
        echo DEBUG=True
        echo ALLOWED_HOSTS=localhost,127.0.0.1
        echo DB_ENGINE=django.db.backends.sqlite3
        echo DB_NAME=db.sqlite3
        echo DB_USER=
        echo DB_PASSWORD=
        echo DB_HOST=
        echo DB_PORT=
        echo TIME_ZONE=America/Argentina/Buenos_Aires
        echo ADMIN_USERNAME=!ADMIN_USERNAME!
        echo ADMIN_EMAIL=!ADMIN_EMAIL!
        echo ADMIN_PASSWORD=!ADMIN_PASSWORD!
        echo RESTAURANT_NAME=!RESTAURANT_NAME!
        echo RESTAURANT_ADDRESS=!RESTAURANT_ADDRESS!
        echo RESTAURANT_PHONE=!RESTAURANT_PHONE!
        echo CURRENCY_SYMBOL=!CURRENCY_SYMBOL!
        echo TAX_PERCENT=!TAX_PERCENT!
    ) > .env
    echo.
    echo [OK] Archivo .env creado
) else (
    echo [OK] Archivo .env existente
)

:: ── Leer .env ─────────────────────────────────────────────
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" set %%A=%%B
)

:: ── Migraciones ───────────────────────────────────────────
echo.
echo [INFO] Ejecutando migraciones...
python manage.py migrate --run-syncdb
if errorlevel 1 ( echo [ERROR] Fallo migrate & pause & exit /b 1 )
echo [OK] Base de datos lista

:: ── Crear superusuario ────────────────────────────────────
echo [INFO] Configurando usuario administrador...
python manage.py shell -c "
from django.contrib.auth.models import User
import os
u = os.environ.get('ADMIN_USERNAME','admin')
p = os.environ.get('ADMIN_PASSWORD','admin123')
e = os.environ.get('ADMIN_EMAIL','')
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u,e,p)
    print(f'[OK] Usuario {u} creado')
else:
    usr = User.objects.get(username=u)
    usr.set_password(p)
    usr.is_staff = True
    usr.is_superuser = True
    usr.save()
    print(f'[OK] Usuario {u} actualizado')
"

:: ── Configurar datos del local ────────────────────────────
echo [INFO] Configurando datos del local...
python manage.py shell -c "
from config.models import SystemSettings
import os
s = SystemSettings.get()
s.restaurant_name = os.environ.get('RESTAURANT_NAME', s.restaurant_name)
s.address = os.environ.get('RESTAURANT_ADDRESS', s.address)
s.phone = os.environ.get('RESTAURANT_PHONE', s.phone)
s.currency_symbol = os.environ.get('CURRENCY_SYMBOL', s.currency_symbol)
tax = os.environ.get('TAX_PERCENT', '0')
from decimal import Decimal
try: s.tax_percent = Decimal(tax)
except: pass
s.save()
print(f'[OK] Local: {s.restaurant_name}')
"

:: ── Static files ──────────────────────────────────────────
echo [INFO] Recolectando archivos estaticos...
python manage.py collectstatic --noinput -v 0
echo [OK] Archivos estaticos listos

:: ── Carpetas necesarias ───────────────────────────────────
if not exist "media\" mkdir media
if not exist "logs\" mkdir logs

:: ── Listo ─────────────────────────────────────────────────
echo.
echo  ══════════════════════════════════════════════════════
echo   DEPLOY COMPLETADO
echo  ══════════════════════════════════════════════════════
echo.
echo   Local:    http://127.0.0.1:8000
echo   Admin:    Usuario: %ADMIN_USERNAME%
echo.

set /p START_NOW="  Iniciar el servidor ahora? (s/n) [s]: "
if /i "!START_NOW!"=="n" goto end

echo.
echo [INFO] Iniciando servidor en http://127.0.0.1:8000 ...
echo [INFO] Presionar Ctrl+C para detener
echo.
python manage.py runserver 0.0.0.0:8000

:end
echo.
echo Para iniciar el servidor manualmente:
echo   .venv\Scripts\activate
echo   python manage.py runserver
echo.
pause
endlocal
