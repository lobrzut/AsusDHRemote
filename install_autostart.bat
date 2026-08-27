@echo off
:: Get directory where the bat script is located (includes trailing slash)
set "SCRIPT_DIR=%~dp0"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AsusDHRemote.lnk"
set "TARGET_PATH=%SCRIPT_DIR%start_hidden.vbs"

echo =========================================================
echo  ASUS DH Remote Autostart Installer
echo =========================================================
echo.
echo Project Folder:  %SCRIPT_DIR%
echo Target Script:    %TARGET_PATH%
echo Shortcut Path:    %SHORTCUT_PATH%
echo.

:: Create Shortcut in Startup folder using PowerShell
powershell -NoProfile -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%TARGET_PATH%'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.Save()"

if %ERRORLEVEL% equ 0 (
    echo.
    echo [+] SUCCESS: ASUS DH Remote service registered to start automatically on login!
) else (
    echo.
    echo [-] ERROR: Failed to register startup shortcut.
)
echo.
pause
