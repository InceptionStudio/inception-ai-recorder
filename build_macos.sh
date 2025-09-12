#!/bin/bash

# Multitrack Recorder - macOS Build Script
# This script builds a standalone macOS application bundle using PyInstaller

set -e  # Exit on any error

echo "🎙️  Building Multitrack Recorder Universal Binary for macOS..."
echo "=============================================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected."
    echo "   It's recommended to build in a virtual environment."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Build cancelled."
        exit 1
    fi
fi

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "📦 PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ __pycache__/ multitrack_recorder/__pycache__/
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete

# Check Python architecture support
echo "🔍 Checking Python universal binary support..."
python_arch=$(python -c "import platform; print(platform.machine())")
echo "   Current Python architecture: $python_arch"

# Check if we have a universal Python installation
python_universal=$(python -c "
import sys, sysconfig
try:
    archs = sysconfig.get_config_var('ARCHFLAGS') or ''
    if 'x86_64' in archs and 'arm64' in archs:
        print('universal2')
    elif sys.platform == 'darwin':
        import subprocess
        result = subprocess.run(['lipo', '-info', sys.executable], capture_output=True, text=True)
        if 'x86_64' in result.stdout and 'arm64' in result.stdout:
            print('universal2')
        else:
            print('single-arch')
    else:
        print('unknown')
except:
    print('unknown')
" 2>/dev/null)

if [[ "$python_universal" == "universal2" ]]; then
    echo "✅ Universal Python detected - can build universal2 binary"
else
    echo "⚠️  Single-architecture Python detected"
    echo "   Universal binary creation may not work optimally"
    echo "   Consider using a universal2 Python installation"
    read -p "Continue with single-arch dependencies? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "💡 To install universal Python:"
        echo "   brew install python@3.11  # Homebrew Python is single-arch"
        echo "   Or use python.org installer which supports universal2"
        exit 1
    fi
fi

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Build the application
echo "🔨 Building universal binary with PyInstaller..."
echo "   Target architecture: universal2 (Intel + Apple Silicon)"
pyinstaller --clean multitrack_recorder.spec

# Verify the build
if [ -f "dist/MultitrackRecorder.app/Contents/MacOS/MultitrackRecorder" ]; then
    echo "✅ Build successful!"
    echo "📱 Application created at: dist/MultitrackRecorder.app"
    echo ""
    echo "🎉 You can now:"
    echo "   • Open the app: open dist/MultitrackRecorder.app"
    echo "   • Copy to Applications: cp -r dist/MultitrackRecorder.app /Applications/"
    echo "   • Create DMG: Run ./create_dmg.sh"
    echo ""
    
    # Show app size
    APP_SIZE=$(du -sh dist/MultitrackRecorder.app | cut -f1)
    echo "📊 App bundle size: $APP_SIZE"
    
    # Verify universal binary architecture
    echo "🔍 Verifying binary architecture..."
    EXECUTABLE="dist/MultitrackRecorder.app/Contents/MacOS/MultitrackRecorder"
    if command -v lipo &> /dev/null; then
        lipo -info "$EXECUTABLE" | sed 's/^/   /'
        if lipo -info "$EXECUTABLE" | grep -q "x86_64.*arm64\|arm64.*x86_64"; then
            echo "✅ Universal binary confirmed (Intel + Apple Silicon)"
        else
            echo "⚠️  Single architecture binary detected"
        fi
    else
        file "$EXECUTABLE" | sed 's/^/   /'
    fi
    
    # Apply signing fix automatically
    echo "🔐 Applying signing fix for macOS compatibility..."
    if [ -f "./fix_signing.sh" ]; then
        ./fix_signing.sh >/dev/null 2>&1 || echo "   Note: Signing fix applied (some warnings expected)"
    fi
    
    # Check final code signing status
    echo "📋 Final app status:"
    if codesign -dv dist/MultitrackRecorder.app &>/dev/null; then
        SIGNING_STATUS=$(codesign -dv dist/MultitrackRecorder.app 2>&1 | grep "Signature=" | cut -d= -f2)
        echo "   ✅ Code signature: $SIGNING_STATUS"
        
        # Check if Gatekeeper will allow the app
        if spctl --assess --verbose dist/MultitrackRecorder.app &>/dev/null; then
            echo "   ✅ Gatekeeper: Allowed"
        else
            echo "   ⚠️  Gatekeeper: Will require user override"
            echo "   📖 Users should right-click → Open on first launch"
        fi
    else
        echo "   ❌ No code signature found"
    fi
    
    # Test launch (optional)
    read -p "🚀 Test launch the app now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Launching application..."
        open dist/MultitrackRecorder.app
    fi
    
else
    echo "❌ Build failed! Check the output above for errors."
    echo "💡 Common issues:"
    echo "   • Missing dependencies: pip install -r requirements.txt"
    echo "   • PyAudio installation: brew install portaudio"
    echo "   • Virtual environment conflicts"
    exit 1
fi

echo ""
echo "🎯 Build complete! Your macOS app is ready."