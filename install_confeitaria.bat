@echo off
setlocal
set "APP_NAME=Confeitaria Deise Brandao"
set "TARGET_DIR=%LOCALAPPDATA%\%APP_NAME%"
set "ZIP_FILE=%~dp0installer_app_package.zip"
set "UNINSTALL_SRC=%~dp0desinstalar_confeitaria.bat"
set "APP_EXE=%TARGET_DIR%\Confeitaria Deise Brandao.exe"

if exist "%TARGET_DIR%" rmdir /S /Q "%TARGET_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP_FILE%' -DestinationPath $env:LOCALAPPDATA -Force"
if errorlevel 1 exit /b 1

copy /Y "%UNINSTALL_SRC%" "%TARGET_DIR%\Desinstalar Confeitaria Deise Brandao.bat" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell = New-Object -ComObject WScript.Shell; $target = Join-Path $env:LOCALAPPDATA 'Confeitaria Deise Brandao\Confeitaria Deise Brandao.exe'; $work = Split-Path $target; $desktop = [Environment]::GetFolderPath('Desktop'); $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'; foreach ($shortcutPath in @((Join-Path $desktop 'Confeitaria Deise Brandao.lnk'), (Join-Path $startMenu 'Confeitaria Deise Brandao.lnk'))) { $shortcut = $shell.CreateShortcut($shortcutPath); $shortcut.TargetPath = $target; $shortcut.WorkingDirectory = $work; $shortcut.IconLocation = $target + ',0'; $shortcut.Save() }"

start "" "%APP_EXE%"
exit /b 0
