#!/bin/bash

# Home Assistant Cloud Integration - Installation Script
# This script installs the custom component to your Home Assistant configuration directory

set -e

echo "🏠 Home Assistant Cloud Integration Installer"
echo "============================================"

# Check if target directory is provided
if [ -z "$1" ]; then
    echo "❌ Error: Please provide your Home Assistant configuration directory path"
    echo ""
    echo "Usage: $0 /path/to/homeassistant/config"
    echo ""
    echo "Examples:"
    echo "  $0 /home/homeassistant/.homeassistant"
    echo "  $0 /config  # For Home Assistant OS/Docker"
    echo "  $0 ~/.homeassistant  # For manual installation"
    exit 1
fi

CONFIG_DIR="$1"
CUSTOM_COMPONENTS_DIR="$CONFIG_DIR/custom_components"
TARGET_DIR="$CUSTOM_COMPONENTS_DIR/your_cloud"

echo "📁 Configuration Directory: $CONFIG_DIR"
echo "📦 Target Directory: $TARGET_DIR"

# Verify Home Assistant config directory exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo "❌ Error: Home Assistant configuration directory not found: $CONFIG_DIR"
    echo "   Please ensure the path is correct and Home Assistant is installed"
    exit 1
fi

# Check for configuration.yaml to confirm it's a HA config directory
if [ ! -f "$CONFIG_DIR/configuration.yaml" ]; then
    echo "⚠️  Warning: configuration.yaml not found in $CONFIG_DIR"
    echo "   This may not be a valid Home Assistant configuration directory"
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 1
    fi
fi

# Create custom_components directory if it doesn't exist
echo "📂 Creating custom_components directory..."
mkdir -p "$CUSTOM_COMPONENTS_DIR"

# Remove existing installation if present
if [ -d "$TARGET_DIR" ]; then
    echo "🔄 Removing existing installation..."
    rm -rf "$TARGET_DIR"
fi

# Create target directory
echo "📦 Creating integration directory..."
mkdir -p "$TARGET_DIR"

# Copy integration files
echo "📋 Copying integration files..."
cp custom_components/your_cloud/*.py "$TARGET_DIR/"
cp custom_components/your_cloud/*.json "$TARGET_DIR/"

echo "✅ Files copied successfully:"
ls -la "$TARGET_DIR"

# Set appropriate permissions
echo "🔒 Setting file permissions..."
chmod 644 "$TARGET_DIR"/*.py "$TARGET_DIR"/*.json

# Copy configuration template (optional)
if [ -f "configuration.yaml.template" ]; then
    echo "📄 Copying configuration template..."
    cp configuration.yaml.template "$CONFIG_DIR/your_cloud_config_example.yaml"
    echo "   Template saved as: $CONFIG_DIR/your_cloud_config_example.yaml"
fi

echo ""
echo "🎉 Installation Complete!"
echo ""
echo "📋 Next Steps:"
echo "   1. Restart Home Assistant"
echo "   2. Go to Settings → Devices & Services"
echo "   3. Click '+ Add Integration'"
echo "   4. Search for 'Home Assistant Cloud'"
echo "   5. Follow the configuration wizard"
echo ""
echo "📖 Documentation:"
echo "   - Configuration guide: See README.md"
echo "   - Example configuration: $CONFIG_DIR/your_cloud_config_example.yaml"
echo "   - Troubleshooting: Enable debug logging for 'custom_components.your_cloud'"
echo ""
echo "🔧 Cloud Backend:"
echo "   Don't forget to deploy the AWS backend from the aws-backend/ directory"
echo "   See aws-backend/README.md for deployment instructions"
echo ""
echo "💡 Tips:"
echo "   - Keep your API key secure"
echo "   - Monitor the integration logs after installation"
echo "   - Use the sync_devices service for manual synchronization"
echo ""
echo "🆘 Need Help?"
echo "   - Check the logs: Settings → System → Logs"
echo "   - GitHub Issues: https://github.com/your-username/homeassistant-cloud-integration/issues"
echo "   - Documentation: https://github.com/your-username/homeassistant-cloud-integration/wiki"