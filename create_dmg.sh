#!/bin/bash

# Multitrack Recorder - DMG Creation Script
# Creates a distributable disk image for the macOS application

set -e  # Exit on any error

APP_NAME="MultitrackRecorder"
DMG_NAME="MultitrackRecorder-Universal-v1.0.0"
SOURCE_DIR="dist"
TEMP_DMG="temp_${DMG_NAME}.dmg"
FINAL_DMG="${DMG_NAME}.dmg"

echo "💿 Creating Universal DMG for Multitrack Recorder..."
echo "===================================================="

# Check if app exists
if [ ! -d "${SOURCE_DIR}/${APP_NAME}.app" ]; then
    echo "❌ Error: ${SOURCE_DIR}/${APP_NAME}.app not found!"
    echo "   Run ./build_macos.sh first to create the app bundle."
    exit 1
fi

# Clean up any existing DMG files
echo "🧹 Cleaning up existing DMG files..."
rm -f "${TEMP_DMG}" "${FINAL_DMG}"

# Create temporary directory for DMG contents
TEMP_DIR=$(mktemp -d)
echo "📁 Creating DMG contents in: ${TEMP_DIR}"

# Copy app bundle to temp directory
echo "📦 Copying application bundle..."
cp -R "${SOURCE_DIR}/${APP_NAME}.app" "${TEMP_DIR}/"

# Create Applications symlink for easy installation
echo "🔗 Creating Applications shortcut..."
ln -s /Applications "${TEMP_DIR}/Applications"

# Copy additional files if they exist
if [ -f "README.md" ]; then
    echo "📄 Adding README..."
    cp README.md "${TEMP_DIR}/"
fi

if [ -f "LICENSE" ]; then
    echo "📋 Adding LICENSE..."
    cp LICENSE "${TEMP_DIR}/"
fi

# Calculate size needed for DMG (with some padding)
echo "📏 Calculating DMG size..."
SIZE_KB=$(du -sk "${TEMP_DIR}" | cut -f1)
SIZE_MB=$(( (SIZE_KB + 10240) / 1024 ))  # Add 10MB padding
echo "💾 DMG size will be: ${SIZE_MB}MB"

# Create the temporary DMG
echo "🔨 Creating temporary DMG..."
hdiutil create -srcfolder "${TEMP_DIR}" -volname "${APP_NAME}" -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" -format UDRW -size ${SIZE_MB}m "${TEMP_DMG}"

# Mount the DMG for customization
echo "🔧 Mounting DMG for customization..."
DEVICE=$(hdiutil attach -readwrite -noverify "${TEMP_DMG}" | \
    egrep '^/dev/' | sed 1q | awk '{print $1}')
MOUNT_POINT="/Volumes/${APP_NAME}"

# Set DMG window properties using AppleScript
echo "🎨 Customizing DMG appearance..."
cat > dmg_setup.applescript << EOF
tell application "Finder"
    tell disk "${APP_NAME}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 100, 920, 420}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 72
        set background picture of viewOptions to file ".background:background.png"
        make new alias file at container window to POSIX file "/Applications" with properties {name:"Applications"}
        set position of item "${APP_NAME}.app" of container window to {160, 205}
        set position of item "Applications" of container window to {360, 205}
        close
        open
        update without registering applications
        delay 2
    end tell
end tell
EOF

# Create background directory and add a simple background
mkdir -p "${MOUNT_POINT}/.background"
# Create a simple background image using system tools
if command -v sips &> /dev/null; then
    sips -s format png --resampleWidth 520 --resampleHeight 320 \
        --setProperty formatOptions 100 app_icon.png \
        --out "${MOUNT_POINT}/.background/background.png" 2>/dev/null || true
fi

# Apply the AppleScript (may fail silently on headless systems)
osascript dmg_setup.applescript 2>/dev/null || echo "⚠️  DMG customization skipped (requires GUI)"

# Clean up
rm -f dmg_setup.applescript

# Sync and unmount
echo "💾 Finalizing DMG..."
sync
hdiutil detach "${DEVICE}"

# Convert to compressed read-only DMG
echo "🗜️  Compressing final DMG..."
hdiutil convert "${TEMP_DMG}" -format UDZO -imagekey zlib-level=9 -o "${FINAL_DMG}"

# Clean up
rm -f "${TEMP_DMG}"
rm -rf "${TEMP_DIR}"

# Verify the final DMG
if [ -f "${FINAL_DMG}" ]; then
    DMG_SIZE=$(du -sh "${FINAL_DMG}" | cut -f1)
    echo "✅ DMG created successfully!"
    echo "📁 Location: ${FINAL_DMG}"
    echo "📊 Size: ${DMG_SIZE}"
    echo ""
    echo "🎉 Your distributable macOS installer is ready!"
    echo "   Users can:"
    echo "   • Double-click to mount: ${FINAL_DMG}"
    echo "   • Drag ${APP_NAME}.app to Applications folder"
    echo "   • Launch from Applications or Launchpad"
    echo ""
    
    # Offer to open the DMG for testing
    read -p "🔍 Open the DMG to test it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "${FINAL_DMG}"
    fi
else
    echo "❌ DMG creation failed!"
    exit 1
fi

echo ""
echo "🚀 Distribution package complete!"