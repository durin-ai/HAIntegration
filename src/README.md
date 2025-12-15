# Home Assistant Cloud Integration

This custom component provides cloud-based device synchronization and control for Home Assistant through AWS services.

## Features

- 🏠 **Device Synchronization**: Automatically sync all your Home Assistant devices and entities to the cloud
- 🔄 **Real-time Updates**: Bidirectional communication for instant state updates
- 🛡️ **Secure**: End-to-end encryption and authentication using AWS security best practices
- 📱 **Remote Control**: Control your devices from anywhere through cloud webhooks
- 🔧 **Easy Setup**: Simple configuration flow with automatic registration
- 📊 **Monitoring**: Built-in automation triggers and event processing
- ⚡ **Scalable**: Serverless AWS architecture that scales with your needs

## Prerequisites

1. **AWS Account**: You need an active AWS account with appropriate permissions
2. **AWS IoT Core**: Deploy the backend infrastructure (see Cloud Backend Setup below)
3. **MQTT Credentials**: Obtain MQTT broker endpoint and credentials from your deployment
4. **Home Assistant**: Version 2024.1.0 or newer

## Installation

### Method 1: HACS (Recommended)

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Go to **HACS** → **Integrations**
3. Click the **⋮** (three dots menu) in the top right → **Custom repositories**
4. Add the repository:
   - **Repository**: `https://github.com/durin-ai/HAIntegration`
   - **Category**: `Integration`
5. Click **Add**
6. Click the **+ Explore & Download Repositories** button
7. Search for **"Durin"** or **"Durin Home Assistant Integration"**
8. Click on it and then click **Download**
9. Restart Home Assistant

**Note**: After installation, you still need to deploy the AWS backend before configuring the integration.

### Method 2: Manual Installation

1. Download the latest release from the [releases page](../../releases)
2. Extract the files to your `custom_components` directory:
   ```
   custom_components/
   └── your_cloud/
       ├── __init__.py
       ├── config_flow.py
       ├── const.py
       ├── manifest.json
       └── strings.json
   ```
3. Restart Home Assistant

### Method 3: Using the Installation Script

This repository includes an installation script for easy setup:

```bash
# Clone this repository
git clone https://github.com/your-username/homeassistant-cloud-integration.git
cd homeassistant-cloud-integration/src

# Make the script executable and run it
chmod +x install.sh
./install.sh /path/to/your/homeassistant/config
```

The script will:
- Copy files to the correct location
- Install Python dependencies
- Provide setup instructions

## Configuration

### Step 1: Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Home Assistant Cloud"
4. Click on it to start the configuration

### Step 2: Enter Your MQTT Credentials

1. **MQTT Broker**: Enter your AWS IoT Core endpoint (e.g., `a1b2c3.iot.us-east-1.amazonaws.com`)
2. **MQTT Port**: Enter `8883` (default for MQTT over TLS)
3. **MQTT Username**: Your MQTT username (if using username/password auth)
4. **MQTT Password**: Your MQTT password (if using username/password auth)
5. **Use TLS**: Enable TLS encryption (recommended)

**Note**: For certificate-based authentication with AWS IoT Core, you may need to configure certificates separately. See the [AWS IoT Core documentation](https://docs.aws.amazon.com/iot/latest/developerguide/protocols.html) for details.

### Step 3: Complete Setup

The integration will automatically:
- Connect to your AWS IoT Core MQTT broker
- Register your Home Assistant instance
- Subscribe to command topics
- Start publishing device states and events

## Cloud Backend Setup

This integration requires a cloud backend to be deployed. The backend is included in the `aws-backend/` directory.

### Deploy the Backend

```bash
cd aws-backend/
npm install
./deploy.sh dev  # Deploy to development environment
```

See the [AWS Backend README](../aws-backend/README.md) for detailed deployment instructions.

## Configuration Options

### Basic Configuration

```yaml
# configuration.yaml.template shows the manual configuration format
# This is automatically handled by the config flow
```

### Advanced Options

After initial setup, you can modify these options via **Settings** → **Devices & Services** → **Your Cloud Integration** → **Configure**:

- **Cloud API URL**: Change the backend URL
- **Sync Interval**: How often to sync devices (default: 5 minutes)
- **Enable Notifications**: Receive alerts for security events

## Services

The integration provides several services you can use in automations:

### `your_cloud.sync_devices`

Manually trigger a device synchronization:

```yaml
service: your_cloud.sync_devices
```

### `your_cloud.send_command`

Send a command to an entity through the cloud:

```yaml
service: your_cloud.send_command
data:
  entity_id: light.living_room
  action: turn_on
  params:
    brightness: 255
    color_name: blue
```

## Automation Examples

### Security Alert Automation

```yaml
automation:
  - alias: "Cloud Security Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: 'on'
    action:
      - service: notify.mobile_app
        data:
          message: "Front door opened - detected by cloud integration"
      - service: your_cloud.send_command
        data:
          entity_id: light.porch
          action: turn_on
```

### Sync Status Monitoring

```yaml
automation:
  - alias: "Monitor Cloud Sync"
    trigger:
      - platform: state
        entity_id: sensor.cloud_last_sync
    condition:
      - condition: template
        value_template: "{{ (as_timestamp(now()) - as_timestamp(trigger.to_state.state)) > 600 }}"
    action:
      - service: persistent_notification.create
        data:
          message: "Cloud sync hasn't run in over 10 minutes"
          title: "Cloud Integration Warning"
```

## Troubleshooting

### Common Issues

1. **"Invalid API Key" Error**
   - Verify your API key is correct
   - Check that your cloud backend is deployed and accessible
   - Ensure your AWS credentials are properly configured

2. **"Connection Failed" Error**
   - Check your internet connection
   - Verify the API URL is correct and accessible
   - Check firewall settings

3. **Devices Not Syncing**
   - Check the integration logs: **Settings** → **System** → **Logs**
   - Verify entities are in supported domains (light, switch, sensor, etc.)
   - Try manual sync: Developer Tools → Services → `your_cloud.sync_devices`

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.your_cloud: debug
```

### Health Checks

The integration provides several diagnostic sensors:
- `sensor.cloud_connection_status`: Connection state
- `sensor.cloud_last_sync`: Last successful sync time
- `sensor.cloud_synced_devices`: Number of synced devices
- `sensor.cloud_synced_entities`: Number of synced entities

## Security Considerations

- **API Keys**: Keep your API keys secure and rotate them regularly
- **Network**: Use HTTPS endpoints only (the default configuration does this)
- **Permissions**: The integration only syncs devices you explicitly allow
- **Data**: Device states are encrypted in transit and at rest in AWS
- **Access**: Cloud access is tied to your specific Home Assistant installation

## Contributing

Contributions are welcome! Please read the [contributing guidelines](CONTRIBUTING.md) first.

### Development Setup

1. Clone the repository
2. Install development dependencies: `pip install -r requirements-dev.txt`
3. Run tests: `pytest`
4. Run linting: `flake8` and `black`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs and feature requests on [GitHub Issues](../../issues)
- **Discussions**: Join the conversation on [GitHub Discussions](../../discussions)
- **Documentation**: Full documentation available in the [wiki](../../wiki)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

## Related Projects

- [Home Assistant](https://www.home-assistant.io/) - The home automation platform
- [HACS](https://hacs.xyz/) - Home Assistant Community Store
- [AWS Serverless](https://aws.amazon.com/serverless/) - The cloud backend infrastructure