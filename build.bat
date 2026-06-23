@echo off
REM JARVIS Desktop - Build Script
REM Builds single-file executable

setlocal enabledelayedexpansion

echo ========================================
echo JARVIS Desktop - Build System
echo ========================================
echo.

REM Configuration
set SPEC_FILE=JARVIS.spec
set OUTPUT_DIR=dist
set EXE_NAME=JARVIS.exe

REM Parse arguments
set CLEAN=0
if "%~1"=="-clean" set CLEAN=1

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    exit /b 1
)

REM Check source
if not exist "jarvis\__init__.py" (
    echo ERROR: Run from JARVIS source directory.
    exit /b 1
)

REM Clean previous builds
if %CLEAN%==1 (
    echo Cleaning previous builds...
    if exist "build" rmdir /s /q build
    if exist "dist" rmdir /s /q dist
    echo Done.
    echo.
)

REM Create resources directory
if not exist "resources" mkdir resources

REM Create icon if missing
if not exist "resources\jarvis.ico" (
    echo Creating default icon...
    python -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (256, 256), color=(30, 60, 90))
draw = ImageDraw.Draw(img)
draw.ellipse([16, 16, 240, 240], fill=(70, 130, 180))
draw.text((90, 70), 'J', fill='white', size=150)
img.save('resources/jarvis.png')
img.save('resources/jarvis.ico')
" 2>nul || echo Icon skipped.
)
echo.

REM Install dependencies
echo Installing build dependencies...
pip install pyinstaller pystray pillow psutil --quiet 2>nul
echo.

REM Build executable
echo ========================================
echo Building JARVIS Executable
echo ========================================
echo.

pyinstaller %SPEC_FILE% --onefile --noconfirm --clean

if errorlevel 1 (
    echo.
    echo ERROR: Build failed.
    exit /b 1
)

REM Verify output
if exist "%OUTPUT_DIR%\%EXE_NAME%" (
    echo.
    echo ========================================
    echo Build Successful!
    echo ========================================
    echo.
    for %%A in ("%OUTPUT_DIR%\%EXE_NAME%") do set SIZE=%%~zA
    set /a MB=%SIZE% / 1048576
    echo Executable: %OUTPUT_DIR%\%EXE_NAME%
    echo Size: ~%MB% MB
    echo.
    echo Build complete!
) else (
    echo ERROR: Executable not found.
    exit /b 1
)

