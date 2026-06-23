@echo off
REM JARVIS Desktop - Startup Configuration
REM Creates shortcuts and auto-start registration

setlocal

echo ========================================
echo JARVIS Desktop - Startup Setup
echo ========================================
echo.

REM Get installation path
set "INSTALL_DIR=%LOCALAPPDATA%\JARVIS"
set "EXE_NAME=JARVIS.exe"

REM Parse arguments
set ACTION=%1
if "%ACTION%"=="" set ACTION=install

if "%ACTION%"=="install" goto :install
if "%ACTION%"=="uninstall" goto :uninstall
if "%ACTION%"=="enable" goto :enable
if "%ACTION%"=="disable" goto :disable

:usage
echo Usage: startup.bat [install^|uninstall^|enable^|disable]
echo.
echo   install   - Install shortcuts and enable auto-start
echo   uninstall - Remove shortcuts and disable auto-start
echo   enable    - Enable auto-start only
echo   disable   - Disable auto-start only
exit /b 1

:install
echo Installing JARVIS shortcuts and auto-start...
echo.

REM Create installation directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo Created directory: %INSTALL_DIR%

REM Copy executable if provided
if exist "dist\JARVIS.exe" (
    copy "dist\JARVIS.exe" "%INSTALL_DIR%\%EXE_NAME%" >nul
    echo Copied executable to installation directory.
)

REM Create Start Menu shortcut
echo Creating Start Menu shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTMENU%\Programs\JARVIS.lnk'); $s.TargetPath = '%INSTALL_DIR%\%EXE_NAME%'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'JARVIS Desktop Assistant'; $s.Save()"

REM Create Desktop shortcut
echo Creating Desktop shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\JARVIS.lnk'); $s.TargetPath = '%INSTALL_DIR%\%EXE_NAME%'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'JARVIS Desktop Assistant'; $s.Save()"

REM Enable auto-start
call :enable

echo.
echo Installation complete!
echo.
echo JARVIS installed to: %INSTALL_DIR%
echo Shortcuts created on Desktop and Start Menu.
echo Auto-start enabled.
goto :end

:uninstall
echo Removing JARVIS shortcuts and auto-start...
echo.

REM Disable auto-start
call :disable

REM Remove shortcuts
echo Removing shortcuts...
del /q "%STARTMENU%\Programs\JARVIS.lnk" 2>nul
del /q "%USERPROFILE%\Desktop\JARVIS.lnk" 2>nul

echo.
echo Uninstallation complete!
echo Shortcuts removed.
echo Auto-start disabled.
goto :end

:enable
echo Enabling auto-start...
echo.

REM Add to Windows startup
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "JARVIS" /t REG_SZ /d "\"%INSTALL_DIR%\%EXE_NAME%\" --hidden" /f >nul 2>&1

echo Auto-start enabled.
goto :eof

:disable
echo Disabling auto-start...
echo.

REM Remove from Windows startup
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "JARVIS" /f >nul 2>&1

echo Auto-start disabled.
goto :eof

:end
echo.
pause
