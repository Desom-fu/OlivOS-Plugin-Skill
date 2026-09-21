@echo off
chcp 65001 >nul
setlocal

rem Install / update the olivos-plugin-developer skill in every local AI client.
rem Double-click this file, or run: install-skill.bat --only codex,grok --dry-run

set "REPO=%~dp0"
set "PY="

where py.exe >nul 2>nul && set "PY=py -3"
if not defined PY where python.exe >nul 2>nul && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY if exist "C:\Program Files\Python313\python.exe" set "PY="C:\Program Files\Python313\python.exe""
if not defined PY if exist "C:\Program Files\Python312\python.exe" set "PY="C:\Program Files\Python312\python.exe""
if not defined PY if exist "C:\Program Files\Python311\python.exe" set "PY="C:\Program Files\Python311\python.exe""

if not defined PY (
    echo [ERROR] Python 3.9+ was not found. Install Python and run this file again.
    pause
    exit /b 1
)

%PY% "%REPO%scripts\install_skill.py" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Done.
) else (
    echo FAILED with exit code %RC%.
)

pause
exit /b %RC%
