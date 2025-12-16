#!/bin/bash

# Deployment script for Durin Home Assistant Integration
# This script deploys the integration to a Samba-mounted Home Assistant config directory

set -e

# Configuration
SOURCE_DIR="/Users/frederik/Documents/GitHub/Durin/HAIntegration/src/custom_components/durin"
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

# Remove old installation if it exists
if [ -d "$TARGET_DIR/$INTEGRATION_NAME" ]; then
    echo "🧹 Cleaning old installation..."
    rm -rf "$TARGET_DIR/$INTEGRATION_NAME"
    echo "✅ Old installation removed"
fi

# Copy new files
echo "📦 Copying new files..."
cp -r "$SOURCE_DIR" "$TARGET_DIR/"

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
