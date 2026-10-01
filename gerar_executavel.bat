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

echo Gerando executavel...
"venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "ConfeitariaDeiseBrandao.spec"

if errorlevel 1 (
    echo Falha ao gerar o executavel.
    pause
    exit /b 1
)

echo.
echo Pronto! Abra a pasta:
echo dist\Confeitaria Deise Brandao
pause
