#!/bin/bash

# Deployment script for Durin Home Assistant Integration
# This script deploys the integration to a Samba-mounted Home Assistant config directory

set -e

# Configuration
SOURCE_DIR="/Users/frederik/Documents/GitHub/Durin/HAIntegration/custom_components/durin"
TARGET_DIR="/Volumes/config/custom_components"
INTEGRATION_NAME="durin"

echo "🚀 Deploying Durin Integration to Home Assistant..."

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Check if Samba share is mounted
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ Error: Target directory not mounted: $TARGET_DIR"
    echo "Please mount the Samba share first."
    exit 1
fi

# Create custom_components directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Remove old Python and JSON files only (preserve icons folder)
if [ -d "$TARGET_DIR/$INTEGRATION_NAME" ]; then
    echo "🧹 Cleaning old installation..."
    rm -f "$TARGET_DIR/$INTEGRATION_NAME/"*.py
    rm -f "$TARGET_DIR/$INTEGRATION_NAME/"*.json
    echo "✅ Old files removed"
else
    echo "📁 Creating integration directory..."
    mkdir -p "$TARGET_DIR/$INTEGRATION_NAME"
fi

# Copy new files (icons are now in root, managed via Samba)
echo "📦 Copying new files..."
cp "$SOURCE_DIR/"*.py "$TARGET_DIR/$INTEGRATION_NAME/"
cp "$SOURCE_DIR/"*.json "$TARGET_DIR/$INTEGRATION_NAME/"
cp "$SOURCE_DIR/"*.png "$TARGET_DIR/$INTEGRATION_NAME/" 2>/dev/null || true

# Copy translations folder if it exists
if [ -d "$SOURCE_DIR/translations" ]; then
    echo "📦 Copying translations..."
    cp "$SOURCE_DIR/translations/"* "$TARGET_DIR/$INTEGRATION_NAME/translations/" 2>/dev/null || true
fi

# Verify deployment
if [ -d "$TARGET_DIR/$INTEGRATION_NAME" ]; then
    echo "✅ Deployment successful!"
    echo ""
    echo "📁 Files deployed to: $TARGET_DIR/$INTEGRATION_NAME"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Home Assistant (Settings → System → Restart)"
    echo "  2. Go to Settings → Devices & Services → Add Integration"
    echo "  3. Search for 'Durin Ecosystem'"
    echo "  4. Enter your 6-digit Durin code"
    echo ""
else
    echo "❌ Deployment failed!"
    exit 1
fi
