#!/bin/bash
# JARVIS Desktop - Build Script for Linux/macOS

set -e

echo "========================================"
echo "JARVIS Desktop - Build System"
echo "========================================"
echo ""

SPEC_FILE="JARVIS.spec"
OUTPUT_DIR="dist"
EXE_NAME="JARVIS"

# Parse arguments
CLEAN=0
if [[ "$1" == "-clean" ]]; then
    CLEAN=1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found."
    exit 1
fi

# Check source
if [ ! -d "jarvis" ]; then
    echo "ERROR: Run from JARVIS source directory."
    exit 1
fi

# Clean previous builds
if [ $CLEAN -eq 1 ]; then
    echo "Cleaning previous builds..."
    rm -rf build dist *.spec.bak
    echo "Done."
    echo ""
fi

# Create resources directory
mkdir -p resources

# Create icon if missing
if [ ! -f "resources/jarvis.png" ]; then
    echo "Creating default icon..."
    python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (256, 256), color=(30, 60, 90))
draw = ImageDraw.Draw(img)
draw.ellipse([16, 16, 240, 240], fill=(70, 130, 180))
draw.text((90, 70), 'J', fill='white', size=150)
img.save('resources/jarvis.png')
" 2>/dev/null || echo "Icon creation skipped."
fi
echo ""

# Install dependencies
echo "Installing build dependencies..."
pip3 install pyinstaller pystray pillow psutil --quiet 2>/dev/null
echo ""

# Build executable
echo "========================================"
echo "Building JARVIS Executable"
echo "========================================"
echo ""

pyinstaller "$SPEC_FILE" --onefile --noconfirm --clean

# Verify output
if [ -f "$OUTPUT_DIR/$EXE_NAME" ]; then
    echo ""
    echo "========================================"
    echo "Build Successful!"
    echo "========================================"
    echo ""
    SIZE=$(du -h "$OUTPUT_DIR/$EXE_NAME" | cut -f1)
    echo "Executable: $OUTPUT_DIR/$EXE_NAME"
    echo "Size: $SIZE"
    echo ""
    echo "Build complete!"
else
    echo "ERROR: Executable not found."
    exit 1
fi
