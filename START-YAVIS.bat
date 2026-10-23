@echo off
setlocal
cd /d "%~dp0"
title YAVIS starten
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3 wurde nicht gefunden.
    echo Bitte Python 3.11 oder neuer von https://www.python.org/downloads/windows/ installieren
    echo und beim Setup "Add python.exe to PATH" aktivieren.
    pause
    exit /b 1
  )
  set "PYTHON=python"
)
echo [1/2] Installiere bzw. aktualisiere benoetigte Python-Pakete ...
%PYTHON% -m pip install --upgrade pip
if errorlevel 1 goto failed
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo [2/2] Starte YAVIS ...
%PYTHON% main.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo YAVIS konnte nicht gestartet werden. Die Fehlermeldung steht oben.
pause
exit /b 1
