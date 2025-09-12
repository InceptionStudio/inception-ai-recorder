#!/bin/bash

# Fix macOS app signing and Gatekeeper issues
# This script re-signs the built application with proper entitlements

set -e

APP_PATH="dist/MultitrackRecorder.app"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ App not found at $APP_PATH"
    echo "   Run ./build_macos.sh first"
    exit 1
fi

echo "🔧 Fixing macOS signing and Gatekeeper issues..."
echo "================================================"

# Remove existing signature
echo "🗑️  Removing existing signature..."
codesign --remove-signature "$APP_PATH" || true

# Sign with entitlements for proper permissions
echo "✍️  Re-signing with entitlements..."
codesign --sign - --entitlements entitlements.plist --force --deep "$APP_PATH"

# Verify the new signature
echo "✅ Verifying signature..."
codesign --verify --verbose "$APP_PATH"

# Check Gatekeeper status
echo "🚦 Checking Gatekeeper status..."
if spctl --assess --verbose "$APP_PATH" 2>/dev/null; then
    echo "✅ App passes Gatekeeper assessment"
else
    echo "⚠️  App will be blocked by Gatekeeper"
    echo ""
    echo "📋 User instructions to bypass Gatekeeper:"
    echo "   1. Right-click the app → Open"
    echo "   2. Or: System Preferences → Security & Privacy → Allow"
    echo "   3. Or disable Gatekeeper temporarily:"
    echo "      sudo spctl --master-disable"
    echo ""
fi

echo "🎉 Signing fix complete!"
echo ""
echo "📱 The app should now launch without installer errors."
echo "   If users still get blocked, they can right-click → Open"