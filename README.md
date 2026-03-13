# Durin Ecosystem - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Connect your Home Assistant to the Durin Ecosystem for seamless smart home control via MQTT.

## Installation

### HACS (Recommended)

HACS will automatically download and place the integration in the correct folder.

1. Open HACS in Home Assistant
2. Click on **Integrations**
3. Click the three dots menu → **Custom repositories**
4. Add `https://github.com/durin-ai/HAIntegration` as an **Integration**
5. Click **Add**, then search for "Durin Ecosystem" and install it
6. Restart Home Assistant

### Manual Installation

> The `config/` directory is your Home Assistant configuration folder — the same one that contains `configuration.yaml`. On most installations this is `/homeassistant/` or `/config/`.

1. Download the latest release from the [Releases page](https://github.com/durin-ai/HAIntegration/releases)
2. Unzip the archive
3. Copy the `custom_components/durin` folder into the `custom_components/` folder inside your HA config directory so the resulting path is:
   ```
   config/custom_components/durin/
   ```
   If the `custom_components/` folder doesn't exist yet, create it.
4. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Durin Ecosystem"
4. Enter your 6-digit Durin code from the mobile app

## Features

- Real-time device sync via MQTT
- Automatic device discovery
- Secure cloud connection with TLS
- Support for lights, switches, sensors, and more

## Getting Your Durin Code

1. Open the Durin mobile app
2. Navigate to your Residence settings
3. Generate a new 6-digit pairing code
4. Enter the code in Home Assistant within 10 minutes

## Support

- [Issue Tracker](https://github.com/durin-ai/HAIntegration/issues)
- [Documentation](https://github.com/durin-ai/HAIntegration)

## License

MIT License
