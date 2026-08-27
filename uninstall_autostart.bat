@echo off
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AsusDHRemote.lnk"

echo =========================================================
echo  ASUS DH Remote Autostart Remover
echo =========================================================
echo.

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    if %ERRORLEVEL% equ 0 (
        echo [+] Removed startup shortcut:
        echo     %SHORTCUT_PATH%
    ) else (
        echo [-] Failed to delete shortcut.
    )
) else (
    echo [=] No startup shortcut found — nothing to remove.
)
echo.
pause
