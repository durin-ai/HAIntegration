# Home Assistant Cloud Backend

AWS serverless backend infrastructure for the Home Assistant Cloud Integration. This backend provides device synchronization, webhook endpoints, and event processing using AWS Lambda, DynamoDB, and EventBridge.

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Home Assistant  │───▶│ API Gateway  │───▶│ Lambda Functions│
│   Integration   │    │              │    │                 │
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

- **🔐 Secure Registration**: API key validation and secure installation registration
- **📦 Device Sync**: Bulk device and entity synchronization from Home Assistant
- **🔄 Real-time Webhooks**: Bidirectional communication for commands and status updates
- **⚡ Event Processing**: Automated triggers and monitoring through EventBridge
- **📊 Monitoring**: CloudWatch integration for logs and metrics
- **🛡️ Security**: IAM-based permissions and encrypted data storage
- **💰 Cost-Effective**: Serverless architecture with pay-per-use pricing
- **🔧 Scalable**: Auto-scaling Lambda functions and DynamoDB

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
- API Gateway (full access)
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
# Run locally (serverless offline)
npm run offline

# View function logs
npm run logs:register
npm run logs:sync
npm run logs:webhook
npm run logs:events

# Invoke functions manually
npm run invoke:register
npm run invoke:sync
npm run invoke:webhook

# Code quality
npm run lint
npm run test
```

## Configuration

### Environment Variables

The following environment variables are automatically configured:

| Variable | Description | Example |
|----------|-------------|---------|
| `TABLE_NAME` | DynamoDB table name | `homeassistant-cloud-backend-dev-data` |
| `EVENT_BUS_NAME` | EventBridge bus name | `homeassistant-cloud-backend-dev-events` |
| `API_GATEWAY_URL` | API Gateway base URL | `https://abc123.execute-api.us-east-1.amazonaws.com/dev` |
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
  register:
    timeout: 30
    memorySize: 256
```

## API Endpoints

After deployment, you'll have these endpoints:

### 1. Registration Endpoint

Register a new Home Assistant installation:

```http
POST /ha/register
Content-Type: application/json

{
  "api_key": "your-api-key-here"
}
```

**Response:**
```json
{
  "installation_id": "uuid-here",
  "webhook_id": "uuid-here", 
  "webhook_url": "https://api.example.com/webhook/uuid-here"
}
```

### 2. Sync Endpoint

Sync devices and entities from Home Assistant:

```http
POST /ha/sync
Authorization: Bearer your-api-key
Content-Type: application/json

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

### 3. Webhook Endpoint

Bidirectional communication endpoint:

```http
POST /webhook/{webhook_id}
Content-Type: application/json

{
  "type": "command",
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

1. **InstallationRegistered**: New installation created
2. **DevicesSynced**: Devices synchronized from HA
3. **CommandSent**: Command sent to device
4. **StatusUpdate**: Status update from HA

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
- `/aws/lambda/homeassistant-cloud-backend-{stage}-register`
- `/aws/lambda/homeassistant-cloud-backend-{stage}-sync`
- `/aws/lambda/homeassistant-cloud-backend-{stage}-webhook`
- `/aws/lambda/homeassistant-cloud-backend-{stage}-eventProcessor`

### Viewing Logs

```bash
# Real-time logs
npm run logs:register -- --tail
npm run logs:sync -- --tail

# Historical logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/homeassistant
```

### Metrics and Alarms

Key metrics to monitor:
- Lambda invocation count and errors
- DynamoDB read/write capacity
- API Gateway 4xx/5xx errors
- EventBridge rule invocations

## Security

### API Key Management

- API keys are hashed (SHA-256) before storage
- Keys are never logged or exposed in responses
- Implement key rotation in your authentication system

### Network Security

- All endpoints use HTTPS
- CORS is configured for web access
- Rate limiting via API Gateway (if configured)

### IAM Permissions

The deployment creates minimal IAM roles:
- Lambda execution roles with specific resource access
- No cross-account access by default
- CloudWatch logging permissions only

### Data Encryption

- Data encrypted in transit (HTTPS/TLS)
- DynamoDB encryption at rest (AWS managed keys)
- CloudWatch logs retention policies applied

## Cost Optimization

### Pricing Estimates

For a typical home with 50 devices syncing every 5 minutes:

- **Lambda**: ~$0.50/month
- **DynamoDB**: ~$1.00/month  
- **API Gateway**: ~$0.10/month
- **EventBridge**: ~$0.05/month

**Total: ~$1.65/month**

### Cost Reduction Tips

1. **Increase sync interval**: Reduce API calls
2. **Filter entities**: Don't sync unnecessary sensors
3. **Use reserved capacity**: For high-volume DynamoDB usage
4. **Optimize Lambda memory**: Right-size memory allocation

## Troubleshooting

### Common Issues

#### 1. Deployment Failures

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name homeassistant-cloud-backend-dev

# Validate serverless config
npx serverless print
```

#### 2. Lambda Function Errors

```bash
# View function logs
npm run logs:register

# Test function locally
npm run invoke:register --data '{"body": "{\"api_key\": \"test-key\"}"}'
```

#### 3. DynamoDB Issues

```bash
# Check table status
aws dynamodb describe-table --table-name homeassistant-cloud-backend-dev-data

# View table items (development only)
aws dynamodb scan --table-name homeassistant-cloud-backend-dev-data --limit 10
```

#### 4. API Gateway Issues

```bash
# Test endpoints directly
curl -X POST https://your-api-url/dev/ha/register \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test-key"}'
```

### Debug Mode

Enable debug logging:

```bash
# Deploy with debug logging
serverless deploy --stage dev --verbose

# Set environment variable for more logging
export SLS_DEBUG=*
serverless deploy
```

## Development

### Local Development

```bash
# Install dependencies
npm install

# Run offline
npm run offline

# Test locally
curl -X POST http://localhost:3000/ha/register \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test-key"}'
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

# Test thoroughly before updating Home Assistant integration
./test-endpoints.sh prod
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