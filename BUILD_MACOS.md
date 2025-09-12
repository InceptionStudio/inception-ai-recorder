# Building Multitrack Recorder Universal Binary for macOS

This guide explains how to create a universal standalone macOS application bundle for the Multitrack Recorder that runs natively on both Intel and Apple Silicon Macs.

## Prerequisites

### System Requirements
- **macOS**: 10.14 (Mojave) or later
- **Python**: 3.8 or later
- **Homebrew** (recommended for dependencies)

### Dependencies
Install the required system dependencies:

```bash
# Install PortAudio (required for PyAudio)
brew install portaudio

# Install Python-Tk (if not already available)
brew install python-tk
```

### Python Environment Setup

**Important for Universal Binaries**: For the best universal binary support, use Python from [python.org](https://www.python.org) which provides universal2 installers. Homebrew Python is single-architecture and may not produce optimal universal binaries.

1. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

3. **Install application dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   > **Note for Apple Silicon Macs**: If PyAudio installation fails, try:
   > ```bash
   > pip install --global-option='build_ext' \
   >     --global-option='-I/opt/homebrew/include' \
   >     --global-option='-L/opt/homebrew/lib' pyaudio
   > ```

## Building the Application

### Quick Build
Run the automated build script:

```bash
./build_macos.sh
```

This script will:
- ✅ Check dependencies
- 🧹 Clean previous builds  
- 🔨 Build the app with PyInstaller
- 📱 Create `dist/MultitrackRecorder.app`
- 🚀 Optionally test launch the app

### Manual Build
If you prefer to build manually:

```bash
# Clean previous builds
rm -rf build/ dist/

# Build with PyInstaller using the spec file
pyinstaller --clean multitrack_recorder.spec
```

## Creating a Distributable DMG

After building the app, create a disk image for distribution:

```bash
./create_dmg.sh
```

This creates `MultitrackRecorder-Universal-v1.0.0.dmg` with:
- 💿 The application bundle
- 🔗 Applications folder shortcut
- 🎨 Customized installer appearance
- 📋 License and documentation

## Build Output

### Application Bundle Structure
```
MultitrackRecorder.app/
├── Contents/
│   ├── Info.plist           # App metadata
│   ├── MacOS/
│   │   └── MultitrackRecorder  # Main executable
│   ├── Resources/           # App icon and resources
│   └── Frameworks/          # Python runtime and dependencies
```

### Installation Methods

**Option 1: Direct Installation**
```bash
# Copy to Applications folder
cp -r dist/MultitrackRecorder.app /Applications/
```

**Option 2: DMG Distribution**
1. Double-click `MultitrackRecorder-v1.0.0.dmg`
2. Drag `MultitrackRecorder.app` to `Applications` folder
3. Eject the DMG
4. Launch from Applications or Launchpad

## Customization Options

### Changing App Identity
Edit `multitrack_recorder.spec` to modify:

```python
# App bundle configuration
app = BUNDLE(
    # ...
    bundle_identifier='com.yourcompany.multitrackrecorder',  # Change this
    info_plist={
        'CFBundleName': 'Your App Name',                     # Change this
        'CFBundleDisplayName': 'Your App Display Name',     # Change this
        # ...
    }
)
```

### App Icon
Replace `app_icon.png` with your custom icon (1024x1024 PNG recommended).

### Version Information
Update version in both:
- `multitrack_recorder.spec` (CFBundleVersion)
- `create_dmg.sh` (DMG_NAME)

## macOS Security & Signing

The build process automatically handles code signing to prevent the `com.apple.installer.pagecontroller error -1`. If users encounter this error:

1. **Right-click the app → Open** (bypasses Gatekeeper)
2. **Or run the signing fix**: `./fix_signing.sh`
3. **See detailed solutions**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

The app is signed with entitlements that request:
- Microphone access for audio recording
- File system access for saving recordings  
- Network access for Google Drive integration

## Troubleshooting

### Common Build Issues

**PyInstaller not found**:
```bash
pip install pyinstaller
```

**PyAudio build errors**:
```bash
# Ensure PortAudio is installed
brew install portaudio

# For Apple Silicon Macs, try architecture-specific build
arch -x86_64 pip install pyaudio
```

**Missing tkinter**:
```bash
brew install python-tk
```

**Import errors during build**:
- Check all dependencies are installed: `pip install -r requirements.txt`
- Ensure virtual environment is activated
- Verify Python version compatibility (3.8+)

### Runtime Issues

**App won't launch**:
- Check macOS security settings (System Preferences → Security & Privacy)
- Try running from Terminal to see error messages:
  ```bash
  ./dist/MultitrackRecorder.app/Contents/MacOS/MultitrackRecorder
  ```

**Audio device access denied**:
- Grant microphone permission in System Preferences → Security & Privacy → Microphone

**Google Drive features not working**:
- Ensure `credentials.json` is in the app bundle or user directory
- Check internet connectivity
- Verify Google Drive API credentials

### Build Performance

**Reducing app bundle size**:
- Remove unnecessary dependencies from `requirements.txt`
- Use `--exclude-module` in PyInstaller spec for unused modules
- Consider using `--onefile` mode (though this may be slower to launch)

**Faster builds**:
- Use `--noconfirm` flag with PyInstaller
- Skip UPX compression by setting `upx=False` in spec file

## Code Signing (Optional)

For distribution outside the Mac App Store, you may want to sign the application:

```bash
# Sign the app bundle (requires Apple Developer account)
codesign --deep --force --verify --verbose \
    --sign "Developer ID Application: Your Name" \
    dist/MultitrackRecorder.app

# Verify signing
codesign --verify --verbose dist/MultitrackRecorder.app
spctl --assess --verbose dist/MultitrackRecorder.app
```

## Advanced Configuration

### PyInstaller Spec File Details

The `multitrack_recorder.spec` file controls:
- **Hidden imports**: Modules PyInstaller might miss
- **Data files**: Icons, documentation, etc.
- **Exclude modules**: Reduce bundle size
- **macOS specific settings**: Info.plist configuration

### Build Automation

For CI/CD pipelines, the build process can be automated:

```bash
# Headless build (no GUI interactions)
export DISPLAY=""
./build_macos.sh

# Skip interactive prompts
yes n | ./build_macos.sh
```

## Support

If you encounter issues:

1. **Check the build output** for specific error messages
2. **Verify all prerequisites** are installed correctly  
3. **Test in a clean virtual environment**
4. **Check PyInstaller documentation** for advanced troubleshooting
5. **Open an issue** with detailed error logs and system information

---

## Universal Binary Support

This build system supports creating universal binaries that run natively on both Intel and Apple Silicon Macs. See [UNIVERSAL_BINARY.md](UNIVERSAL_BINARY.md) for detailed information about:

- Universal binary creation requirements
- Python installation recommendations  
- Architecture detection and fallback behavior
- Troubleshooting universal build issues

**Current behavior**: The build script auto-detects your Python capabilities and creates the best possible binary for your environment.

---

**🎉 Happy building!** Your users will appreciate having a native macOS application they can easily install and use.