# Troubleshooting macOS Application Issues

This guide helps resolve common issues when running the Multitrack Recorder on macOS.

## Error: "com.apple.installer.pagecontroller error -1"

### What This Means
This error occurs when macOS's Gatekeeper security system blocks the application from launching because:
- The app isn't signed by an Apple Developer certificate
- The app signature doesn't meet current security requirements
- The app was downloaded from an "unidentified developer"

### Solutions (Try in Order)

#### 1. Right-Click to Open (Recommended)
```
1. Right-click on MultitrackRecorder.app
2. Select "Open" from the context menu
3. Click "Open" when the security warning appears
4. The app will be permanently allowed to run
```

#### 2. System Preferences Override
```
1. Try to open the app normally (it will be blocked)
2. Go to System Preferences → Security & Privacy → General
3. Click "Open Anyway" next to the blocked app message
4. Confirm when prompted
```

#### 3. Manual Signing Fix
If the app still won't launch, apply the signing fix:
```bash
./fix_signing.sh
```

#### 4. Terminal Launch (Advanced)
Launch from Terminal to see detailed error messages:
```bash
./dist/MultitrackRecorder.app/Contents/MacOS/MultitrackRecorder
```

### For Developers: Preventing This Issue

#### Option 1: Automatic Fix (Already Implemented)
The build process now automatically applies signing fixes:
```bash
./build_macos.sh  # Includes automatic signing fix
```

#### Option 2: Apple Developer Certificate
For wide distribution, sign with a valid certificate:
```bash
codesign --sign "Developer ID Application: Your Name" \
         --deep --force --options runtime \
         --entitlements entitlements.plist \
         dist/MultitrackRecorder.app
```

## Other Common Issues

### "App is damaged and can't be opened"

**Cause**: Quarantine attribute from download or corrupted signature

**Solution**:
```bash
# Remove quarantine attribute
xattr -dr com.apple.quarantine dist/MultitrackRecorder.app

# Re-sign the app
codesign --sign - --force --deep dist/MultitrackRecorder.app
```

### "Permission denied" When Accessing Microphone

**Cause**: macOS microphone permission not granted

**Solution**:
```
1. System Preferences → Security & Privacy → Privacy
2. Select "Microphone" from the list
3. Check the box next to "MultitrackRecorder"
4. Restart the application
```

### App Launches But Can't Record Audio

**Symptoms**: 
- No audio devices shown
- Recording fails immediately
- "No audio devices found" error

**Solutions**:
1. **Check audio device connections**
2. **Grant microphone permission** (see above)
3. **Restart audio system**:
   ```bash
   sudo killall coreaudiod
   ```
4. **Check device availability**:
   - Go to System Preferences → Sound → Input
   - Verify devices appear and work

### App Crashes on Launch

**Debugging Steps**:
1. **Launch from Terminal** to see crash logs:
   ```bash
   ./dist/MultitrackRecorder.app/Contents/MacOS/MultitrackRecorder
   ```

2. **Check Console app** for crash reports:
   - Applications → Utilities → Console
   - Look for MultitrackRecorder crash reports

3. **Common causes and fixes**:
   - **Missing dependencies**: Reinstall with `pip install -r requirements.txt`
   - **Architecture mismatch**: Rebuild for your system architecture
   - **Corrupt build**: Clean build with `rm -rf build/ dist/` and rebuild

### "PyAudio not found" or Audio Errors

**Solution**:
```bash
# Reinstall PortAudio and PyAudio
brew install portaudio
pip uninstall pyaudio
pip install pyaudio

# For Apple Silicon Macs, try:
pip install --global-option='build_ext' \
    --global-option='-I/opt/homebrew/include' \
    --global-option='-L/opt/homebrew/lib' pyaudio
```

### Universal Binary Issues

**Symptoms**: App runs slowly or through Rosetta on wrong architecture

**Check current architecture**:
```bash
lipo -info dist/MultitrackRecorder.app/Contents/MacOS/MultitrackRecorder
```

**For universal binary**, see [UNIVERSAL_BINARY.md](UNIVERSAL_BINARY.md)

## Gatekeeper Bypass Methods (Advanced)

⚠️ **Warning**: These methods reduce security. Use only for development/testing.

### Temporary Gatekeeper Disable
```bash
# Disable Gatekeeper (requires admin password)
sudo spctl --master-disable

# Re-enable later (recommended)
sudo spctl --master-enable
```

### Allow Unsigned Applications
```bash
# Allow any unsigned app to run
sudo spctl --global-disable

# More targeted: allow specific app
sudo xattr -rd com.apple.quarantine /path/to/MultitrackRecorder.app
```

## Getting Help

If these solutions don't work:

1. **Check the build output** for errors during creation
2. **Test on a different Mac** to isolate the issue  
3. **Verify all dependencies** are properly installed
4. **Create an issue** with:
   - macOS version and chip type (Intel/Apple Silicon)
   - Complete error messages
   - Terminal output from launching the app
   - Results of `codesign -dv dist/MultitrackRecorder.app`

## Prevention for End Users

**For App Distributors**:
- Include these instructions with your app distribution
- Consider getting an Apple Developer certificate for seamless installation
- Test on multiple macOS versions and architectures

**For End Users**:
- Always download from trusted sources
- Use the right-click → Open method for unsigned apps
- Keep macOS updated for the latest security features

---

**🛡️ Remember**: These security measures exist to protect your Mac. Only bypass them for applications you trust completely.