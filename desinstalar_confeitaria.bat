@echo off
setlocal
set "APP_NAME=Confeitaria Deise Brandao"
set "TARGET_DIR=%LOCALAPPDATA%\%APP_NAME%"
set "DESKTOP_SHORTCUT=%USERPROFILE%\Desktop\Confeitaria Deise Brandao.lnk"
set "STARTMENU_SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Confeitaria Deise Brandao.lnk"

if exist "%DESKTOP_SHORTCUT%" del /F /Q "%DESKTOP_SHORTCUT%"
if exist "%STARTMENU_SHORTCUT%" del /F /Q "%STARTMENU_SHORTCUT%"
if exist "%TARGET_DIR%" rmdir /S /Q "%TARGET_DIR%"

pause
