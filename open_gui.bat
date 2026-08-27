@echo off
setlocal enabledelayedexpansion

:: Find all python.exe on PATH and test them
for /f "tokens=*" %%p in ('where python.exe') do (
    "%%p" -c "import pystray, PIL, hid" >nul 2>nul
    if !ERRORLEVEL! equ 0 (
        start "" "%%p" "%~dp0asus_dh_service.py" --gui
        exit /b
    )
)

:: Try py.exe fallback
where py.exe >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" py.exe "%~dp0asus_dh_service.py" --gui
    exit /b
)

echo [-] ERROR: Python with required dependencies (hid, pystray, pillow) was not found!
echo Please make sure you ran: pip install -r requirements.txt
pause
