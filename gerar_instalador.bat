@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado.
    pause
    exit /b 1
)

"venv\Scripts\python.exe" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    "venv\Scripts\python.exe" -m pip install pyinstaller
    if errorlevel 1 (
        echo Falha ao instalar o PyInstaller.
        pause
        exit /b 1
    )
)

echo Gerando instalador...
"venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "Instalador Confeitaria Deise Brandao" --icon "static\img\logo.ico" --add-data "installer_app_package.zip;." "installer_launcher.py"

if errorlevel 1 (
    echo Falha ao gerar o instalador.
    pause
    exit /b 1
)

echo.
echo Pronto! O instalador ficou em:
echo dist\Instalador Confeitaria Deise Brandao.exe
pause
