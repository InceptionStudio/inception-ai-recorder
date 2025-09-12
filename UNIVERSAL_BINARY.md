# Universal Binary Creation Guide

This guide explains how to create universal binaries for the Multitrack Recorder that run natively on both Intel and Apple Silicon Macs.

## What are Universal Binaries?

Universal binaries (also called "fat binaries") contain code for multiple architectures in a single executable file. On macOS, this typically means:
- **x86_64**: Intel-based Macs
- **arm64**: Apple Silicon Macs (M1, M2, M3, etc.)

## Current Implementation

The project includes **two approaches** for universal binary creation:

### 1. Auto-Detecting Build (Recommended)
- **File**: `multitrack_recorder.spec`
- **Behavior**: Automatically detects your Python installation capabilities
- **Result**: Creates universal2 binary if possible, otherwise single-arch for current platform
- **Command**: `./build_macos.sh`

### 2. Force Universal Build
- **File**: `multitrack_recorder_universal.spec`
- **Behavior**: Forces universal2 binary creation (will fail if not supported)
- **Result**: Always attempts universal2 or fails with clear error message
- **Command**: `pyinstaller --clean multitrack_recorder_universal.spec`

## Requirements for True Universal Binaries

To create **true universal2 binaries**, you need:

### ✅ Universal Python Installation
```bash
# Check your Python architecture
python -c "import subprocess; print(subprocess.run(['lipo', '-info', __import__('sys').executable], capture_output=True, text=True).stdout)"
```

**Recommended Python sources for universal2 support:**
- **python.org installer** ✅ (includes universal2 binaries)
- **pyenv with universal2 build** ✅
- **Homebrew Python** ❌ (single-architecture only)
- **Anaconda/Miniconda** ❌ (single-architecture only)

### ✅ Universal Dependencies
All binary dependencies (PyAudio, numpy, etc.) must also be universal2:
```bash
# Check dependency architectures
lipo -info /path/to/dependency.so
```

## Installation Options for Universal2 Support

### Option 1: Python.org Installer (Easiest)
1. Download Python from [python.org](https://www.python.org)
2. Install the universal2 installer
3. Create virtual environment with this Python

### Option 2: pyenv with Universal2 Build
```bash
# Install pyenv
brew install pyenv

# Build Python with universal2 support
env PYTHON_CONFIGURE_OPTS="--enable-universalsdk --with-universal-archs=universal2" pyenv install 3.11.8

# Use the universal Python
pyenv local 3.11.8
python -m venv venv_universal
source venv_universal/bin/activate
```

### Option 3: Manual Universal Environment
If you have access to both Intel and Apple Silicon Macs:
1. Build on Intel Mac with `target_arch='x86_64'`
2. Build on Apple Silicon Mac with `target_arch='arm64'`  
3. Combine using `lipo`:
```bash
lipo -create -output MultitrackRecorder_universal \
    MultitrackRecorder_x86_64 MultitrackRecorder_arm64
```

## Current Build Behavior

The auto-detecting build script will:

1. **Check Python architecture**:
   ```
   📱 Universal Python detected - building universal2 binary
   ✅ Universal binary confirmed (Intel + Apple Silicon)
   ```
   OR
   ```
   📱 Single-arch Python detected - building for current architecture
   ⚠️ Single architecture binary detected
   ```

2. **Create appropriate binary**:
   - Universal2 if Python supports it
   - Single-arch ARM64 (current system) if not

3. **Verify final result** with `lipo -info`

## Testing Universal Binaries

### On Current Machine
```bash
# Build the app
./build_macos.sh

# Check architecture
lipo -info dist/MultitrackRecorder.app/Contents/MacOS/MultitrackRecorder

# Expected outputs:
# Universal: "Architectures in the fat file: x86_64 arm64"
# Single-arch: "Non-fat file: ... is architecture: arm64"
```

### On Different Architectures
- **Intel Mac**: Should run natively without Rosetta
- **Apple Silicon Mac**: Should run natively at full speed
- **Universal2**: Choose optimal architecture automatically

## Troubleshooting Universal Builds

### Error: "is not a fat binary!"
```
PyInstaller.utils.osx.IncompatibleBinaryArchError: _struct.cpython-313-darwin.so is not a fat binary!
```
**Solution**: Your Python installation or dependencies don't support universal2. Use the auto-detecting build instead.

### Error: Dependency Architecture Mismatch
**Solutions**:
1. Install universal2 Python from python.org
2. Use `pip install --force-reinstall` to get universal2 wheels
3. Build dependencies from source with universal2 flags

### Large Binary Size
Universal binaries are typically 1.5-2x larger than single-arch binaries because they contain code for both architectures.

**Current sizes**:
- Single-arch ARM64: ~51MB
- Universal2: ~80-100MB (estimated)

## Build Script Options

The build script accepts environment variables to control behavior:

```bash
# Force architecture (overrides auto-detection)
export PYINSTALLER_TARGET_ARCH=universal2
./build_macos.sh

# Skip architecture checks
export SKIP_ARCH_CHECK=1
./build_macos.sh

# Build with specific spec file
pyinstaller --clean multitrack_recorder_universal.spec
```

## Distribution Considerations

### Universal2 Benefits
- ✅ Single binary works on all Macs
- ✅ Optimal performance on each architecture  
- ✅ Simplified distribution (one DMG)
- ✅ No Rosetta2 required

### Single-Arch Considerations
- ✅ Smaller download size
- ✅ Easier to build (no special requirements)
- ❌ May require Rosetta2 on different architecture
- ❌ Potential performance impact under emulation

## Current Status

The project is configured to:
- **Primary**: Auto-detect capabilities and build best possible binary
- **Fallback**: Provide clear instructions for universal2 setup
- **Alternative**: Force universal2 build with dedicated spec file

**Your current build produces**: ARM64 single-architecture binary (51MB) that runs natively on Apple Silicon and under Rosetta2 on Intel Macs.

**To upgrade to universal2**: Install Python from python.org and rebuild with the same commands.

---

**🎯 Ready to distribute!** Your application will run on all macOS systems with the current single-arch build, and can be upgraded to universal2 for optimal performance across all Mac architectures.