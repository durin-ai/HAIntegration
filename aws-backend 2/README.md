# Durin MQTT Backend

AWS serverless backend infrastructure for the Durin Home Assistant Integration using AWS IoT Core and MQTT protocol. This backend provides device synchronization, real-time messaging, and event processing through MQTT pub/sub architecture.

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Home Assistant  │───▶│ AWS IoT Core │───▶│ Lambda Functions│
│   Integration   │MQTT│  (Broker)    │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                       │
                              ▼                       ▼
                       ┌──────────────┐    ┌─────────────────┐
                       │   CloudWatch │    │    DynamoDB     │
                       │     Logs     │    │     Tables      │
                       └──────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────┐
                                           │   EventBridge   │
                                           │      Bus        │
                                           └─────────────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────┐
                                           │ Event Processor │
                                           │    Lambda       │
                                           └─────────────────┘
```

## Features

- **🔐 Secure MQTT**: TLS-encrypted MQTT connections via AWS IoT Core
- **📦 Device Synchronization**: Real-time device and entity synchronization
- **🔄 Bi-directional Messaging**: Pub/sub pattern for commands and status updates
- **⚡ Event Processing**: Automated triggers and monitoring through EventBridge
- **📊 Monitoring**: CloudWatch integration for logs and metrics
- **🛡️ Security**: AWS IoT authentication and encrypted data storage
- **💰 Cost-Effective**: Serverless architecture with pay-per-use pricing
- **🔧 Scalable**: Auto-scaling Lambda and managed IoT Core broker

## Prerequisites

Before deploying this backend, ensure you have:

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Node.js** version 18 or higher
4. **Serverless Framework** (installed via npm)

### AWS Permissions Required

Your AWS user/role needs these permissions:
- CloudFormation (full access)
- Lambda (full access)
- DynamoDB (full access)
- EventBridge (full access)
- **AWS IoT Core** (full access)
- IAM (role creation)
- CloudWatch (logs)
- SNS (optional, for notifications)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/your-username/homeassistant-cloud-integration.git
cd homeassistant-cloud-integration/aws-backend
npm install
```

### 2. Deploy to Development

```bash
# Deploy to dev environment (default)
./deploy.sh

# Or specify stage and region
./deploy.sh dev us-east-1
```

### 3. Test the Deployment

```bash
# Run the test suite
./test-endpoints.sh dev
```

### 4. Deploy to Production

```bash
# Deploy to production environment
./deploy.sh prod us-east-1
```

## Deployment Commands

### Using the Deploy Script (Recommended)

```bash
# Deploy to development
./deploy.sh dev

# Deploy to production with custom region
./deploy.sh prod eu-west-1

# Deploy to staging
./deploy.sh staging us-west-2
```

The deployment script will:
1. Deploy the serverless infrastructure
2. Retrieve the AWS IoT Core endpoint URL
3. Save the endpoint to a configuration file for use in Home Assistant

### Using Serverless Commands Directly

```bash
# Deploy to specific stage
npm run deploy:dev
npm run deploy:prod

# Remove deployment
npm run remove:dev
npm run remove:prod

# View deployment info
npm run info
```

### Development Commands

```bash
# View function logs
npm run logs:mqtt
npm run logs:events

# Invoke functions manually  
npm run invoke:mqtt

# Code quality
npm run lint
npm run test
```

## MQTT Topics

The backend uses the following MQTT topic structure:

| Topic Pattern | Direction | Purpose |
|--------------|-----------|---------|
| `durin/ha/{installation_id}/register` | Device → Cloud | Register new installation |
| `durin/ha/{installation_id}/sync` | Device → Cloud | Synchronize devices/entities |
| `durin/ha/{installation_id}/status` | Device → Cloud | Publish entity state changes |
| `durin/ha/{installation_id}/events` | Device → Cloud | Send Home Assistant events |
| `durin/ha/{installation_id}/commands` | Cloud → Device | Send commands to Home Assistant |
| `durin/ha/{installation_id}/ack` | Cloud → Device | Acknowledgment messages |

### Topic Wildcards

The IoT Rule uses the following pattern to route all messages:
```
durin/ha/+/#
```

Where:
- `+` matches a single level (installation_id)
- `#` matches remaining levels (message type)

## Configuration

### Environment Variables

The following environment variables are automatically configured:

| Variable | Description | Example |
|----------|-------------|---------|
| `TABLE_NAME` | DynamoDB table name | `durin-mqtt-backend-dev-data` |
| `EVENT_BUS_NAME` | EventBridge bus name | `durin-mqtt-backend-dev-events` |
| `IOT_ENDPOINT` | AWS IoT Core endpoint | `a1b2c3d4e5f6g7.iot.us-east-1.amazonaws.com` |
| `NOTIFICATION_TOPIC_ARN` | SNS topic ARN (optional) | `arn:aws:sns:us-east-1:123456789:notifications` |

### Serverless Configuration

Key configuration options in `serverless.yml`:

```yaml
# Stage and region
provider:
  stage: ${opt:stage, 'dev'}
  region: ${opt:region, 'us-east-1'}

# Function timeout and memory
functions:
  mqttProcessor:
    timeout: 30
    memorySize: 256
```

## Message Processing

After deployment, messages are processed via MQTT topics:

### 1. Registration Message

Publish to register a new Home Assistant installation:

**Topic:** `durin/ha/{installation_id}/register`

**Payload:**
```json
{
  "installation_id": "uuid-here",
  "ha_version": "2024.1.0",
  "installation_name": "My Home"
}
```

**Acknowledgment (Cloud → Device):**
```json
{
  "status": "registered",
  "installation_id": "uuid-here",
  "registered_at": "2024-01-01T00:00:00Z"
}
```

### 2. Sync Message

Publish to synchronize devices and entities:

**Topic:** `durin/ha/{installation_id}/sync`

**Payload:**
```json
{
  "installation_id": "uuid-here",
  "devices": [
    {
      "device_id": "device-1",
      "name": "Living Room Light",
      "manufacturer": "Philips",
      "model": "Hue Bulb",
      "entities": [
        {
          "entity_id": "light.living_room",
          "name": "Living Room Light",
          "device_class": "light",
          "state": "on",
          "attributes": {"brightness": 255}
        }
      ]
    }
  ]
}
```

### 3. Status Updates

Publish entity state changes:

**Topic:** `durin/ha/{installation_id}/status`

**Payload:**
```json
{
  "entity_id": "light.living_room",
  "state": "on",
  "attributes": {"brightness": 128},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 4. Commands (Cloud → Device)

Subscribe to receive commands:

**Topic:** `durin/ha/{installation_id}/commands`

**Payload:**
```json
{
  "command_id": "cmd-uuid",
  "action": "turn_on",
  "entity_id": "light.living_room",
  "params": {"brightness": 128}
}
```

## Data Storage

### DynamoDB Table Structure

The main table uses a single-table design with these access patterns:

| PK | SK | Description |
|----|----|----|
| `INSTALL#{id}` | `METADATA` | Installation metadata and API key hash |
| `INSTALL#{id}` | `DEVICE#{device_id}` | Device information |
| `INSTALL#{id}` | `ENTITY#{entity_id}` | Entity state and attributes |
| `INSTALL#{id}` | `METRICS` | Installation metrics and counters |

### GSI Structure

Global Secondary Index for cross-installation queries:

| GSI1PK | GSI1SK | Use Case |
|--------|--------|----------|
| `ENTITY#{entity_id}` | `INSTALL#{id}` | Find installations with specific entity |
| `WEBHOOK#{webhook_id}` | `INSTALL#{id}` | Webhook to installation mapping |

## Event Processing

### EventBridge Events

The system generates these event types:

1. **InstallationRegistered**: New installation created via MQTT
2. **DevicesSynced**: Devices synchronized from HA via MQTT
3. **CommandSent**: Command sent to device via MQTT topic
4. **StatusUpdate**: Status update from HA via MQTT

### Example Event Processing

```javascript
// Automatic security alerts
if (entity.entity_id.includes('alarm') && entity.state === 'triggered') {
  await sendNotification('🚨 SECURITY ALERT: Alarm triggered!');
  await emitSecurityEvent(installation_id, entity);
}
```

## Monitoring and Logging

### CloudWatch Logs

Each Lambda function has dedicated log groups:
- `/aws/lambda/durin-mqtt-backend-{stage}-mqttProcessor`
- `/aws/lambda/durin-mqtt-backend-{stage}-eventProcessor`
- `/aws/lambda/durin-mqtt-backend-{stage}-iotEndpointProvider`

### Viewing Logs

```bash
# Real-time logs
npm run logs:mqtt -- --tail

# Historical logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/durin-mqtt
```

### IoT Core Monitoring

Monitor MQTT-specific metrics:
- Message publish/receive count
- Connection attempts and failures
- Rule execution count and errors
- Message size and throttling

### Metrics and Alarms

Key metrics to monitor:
- Lambda invocation count and errors
- DynamoDB read/write capacity
- IoT Core message count and rule failures
- EventBridge rule invocations

## Security

### MQTT Authentication

- X.509 certificate-based authentication
- TLS 1.2+ encryption for all MQTT connections
- Certificate policies and thing groups for access control
- Automatic certificate rotation support

### IoT Core Policies

The deployment creates IoT policies with minimal permissions:
- Publish/subscribe permissions scoped to installation-specific topics
- Connect permissions restricted to specific client IDs
- No wildcard permissions by default

### Network Security

- All MQTT connections use TLS encryption (port 8883)
- MQTT over WebSockets available for browser clients
- VPC endpoints support for private connectivity

### IAM Permissions

The deployment creates minimal IAM roles:
- Lambda execution roles with specific resource access
- IoT Core rule permissions for Lambda invocation
- CloudWatch logging permissions only

### Data Encryption

- Data encrypted in transit (TLS 1.2+)
- DynamoDB encryption at rest (AWS managed keys)
- CloudWatch logs retention policies applied
- IoT message encryption in transit

## Cost Optimization

### Pricing Estimates

For a typical home with 50 devices syncing every 5 minutes:

- **Lambda**: ~$0.50/month
- **DynamoDB**: ~$1.00/month  
- **IoT Core**: ~$0.50/month (messaging)
- **EventBridge**: ~$0.05/month

**Total: ~$2.05/month**

### Cost Reduction Tips

1. **Increase sync interval**: Reduce MQTT message frequency
2. **Filter entities**: Don't sync unnecessary sensors
3. **Use reserved capacity**: For high-volume DynamoDB usage
4. **Optimize Lambda memory**: Right-size memory allocation
5. **Batch messages**: Combine multiple updates when possible

## Troubleshooting

### Common Issues

#### 1. Deployment Failures

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name durin-mqtt-backend-dev

# Validate serverless config
npx serverless print
```

#### 2. Lambda Function Errors

```bash
# View function logs
npm run logs:mqtt

# Test IoT Core rule
aws iot-data publish \
  --topic durin/ha/test-install-id/register \
  --payload '{"installation_id":"test-install-id"}' \
  --endpoint your-iot-endpoint.iot.region.amazonaws.com
```

#### 3. DynamoDB Issues

```bash
# Check table status
aws dynamodb describe-table --table-name durin-mqtt-backend-dev-data

# View table items (development only)
aws dynamodb scan --table-name durin-mqtt-backend-dev-data --limit 10
```

#### 4. MQTT Connection Issues

```bash
# Test MQTT connectivity
aws iot describe-endpoint --endpoint-type iot:Data-ATS

# Check IoT Core logs
aws logs tail /aws/iot/logs --follow

# Verify IoT policy
aws iot get-policy --policy-name durin-mqtt-policy
```

#### 5. Certificate Authentication Issues

```bash
# List attached certificates
aws iot list-principal-things --principal "arn:aws:iot:region:account:cert/cert-id"

# Check certificate status
aws iot describe-certificate --certificate-id "cert-id"
```

### Debug Mode

Enable debug logging:

```bash
# Deploy with debug logging
serverless deploy --stage dev --verbose

# Enable IoT Core logging
aws iot set-v2-logging-options --role-arn "arn:aws:iam::account:role/IoTLoggingRole" --default-log-level DEBUG

# Set environment variable for more logging
export SLS_DEBUG=*
serverless deploy
```

## Development

### Local MQTT Testing

```bash
# Install mosquitto MQTT client
brew install mosquitto  # macOS
apt-get install mosquitto-clients  # Linux

# Subscribe to test topic
mosquitto_sub -h your-iot-endpoint.iot.region.amazonaws.com -p 8883 \
  --cert ~/certs/certificate.pem.crt \
  --key ~/certs/private.pem.key \
  --cafile ~/certs/AmazonRootCA1.pem \
  -t 'durin/ha/+/#'

# Publish test message
mosquitto_pub -h your-iot-endpoint.iot.region.amazonaws.com -p 8883 \
  --cert ~/certs/certificate.pem.crt \
  --key ~/certs/private.pem.key \
  --cafile ~/certs/AmazonRootCA1.pem \
  -t 'durin/ha/test-id/register' \
  -m '{"installation_id":"test-id"}'
```

### Testing

```bash
# Run unit tests
npm run test:unit

# Run integration tests (requires AWS credentials)
npm run test:integration

# Run all tests with coverage
npm test
```

### Code Quality

```bash
# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Validate serverless config
npm run validate
```

## Deployment Pipeline

### CI/CD with GitHub Actions

Example workflow:

```yaml
name: Deploy Backend
on:
  push:
    branches: [main]
    paths: ['aws-backend/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd aws-backend && npm ci
      - run: cd aws-backend && npm test
      - run: cd aws-backend && npx serverless deploy --stage prod
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Multi-Environment Strategy

```bash
# Development environment
./deploy.sh dev us-east-1

# Staging environment  
./deploy.sh staging us-east-1

# Production environment
./deploy.sh prod us-east-1
```

## Migration and Upgrades

### Upgrading the Backend

```bash
# Backup current deployment info
npm run info > backup-info.txt

# Deploy new version
./deploy.sh prod

# Verify IoT endpoint is accessible
aws iot describe-endpoint --endpoint-type iot:Data-ATS

# Monitor deployment
npm run logs:mqtt -- --tail
```

### Certificate Management

When rotating certificates:

```bash
# Create new certificate
aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile certificate.pem.crt \
  --public-key-outfile public.pem.key \
  --private-key-outfile private.pem.key

# Attach policy to certificate
aws iot attach-policy \
  --policy-name durin-mqtt-policy \
  --target "arn:aws:iot:region:account:cert/cert-id"

# Update Home Assistant integration with new certificate
```

### Data Migration

When updating table schemas:

1. Deploy new version alongside existing
2. Migrate data using DynamoDB streams
3. Switch traffic to new version
4. Remove old resources

## Support and Contributing

### Getting Help

- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs on GitHub Issues
- **Logs**: Always include CloudWatch logs when reporting issues
- **Testing**: Use the test script to verify functionality

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### License

MIT License - see LICENSE file for details.