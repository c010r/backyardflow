@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Entorno virtual no encontrado. Ejecutá deploy.bat primero.
    pause & exit /b 1
)

call .venv\Scripts\activate.bat

if not exist ".env" (
    echo [ERROR] Archivo .env no encontrado.
    pause & exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" (
        set "val=%%B"
        setlocal EnableDelayedExpansion
        set "val=!val:'=!"
        endlocal & set "%%A=!val!"
    )
)

python manage.py gestionar_usuarios
pause
