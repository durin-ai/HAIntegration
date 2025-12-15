const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, GetCommand, QueryCommand, UpdateCommand } = require('@aws-sdk/lib-dynamodb');
const { EventBridgeClient, PutEventsCommand } = require('@aws-sdk/client-eventbridge');
const { SNSClient, PublishCommand } = require('@aws-sdk/client-sns');

const ddbClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(ddbClient);
const eventBridge = new EventBridgeClient({});
const sns = new SNSClient({});

const TABLE_NAME = process.env.TABLE_NAME;
const EVENT_BUS_NAME = process.env.EVENT_BUS_NAME;
const NOTIFICATION_TOPIC_ARN = process.env.NOTIFICATION_TOPIC_ARN; // Optional SNS topic

exports.handler = async (event) => {
  console.log('EventBridge event received:', JSON.stringify(event, null, 2));
  
  try {
    // Handle different event types
    for (const record of event.Records || [event]) {
      const detail = record.detail || record;
      const eventType = record['detail-type'] || event['detail-type'];
      
      await processEvent(eventType, detail);
    }
    
    return { statusCode: 200 };
  } catch (error) {
    console.error('Event processing error:', error);
    return { statusCode: 500, error: error.message };
  }
};

async function processEvent(eventType, detail) {
  console.log(`Processing event type: ${eventType}`);
  
  switch (eventType) {
    case 'DevicesSynced':
      await handleDevicesSynced(detail);
      break;
      
    case 'InstallationRegistered':
      await handleInstallationRegistered(detail);
      break;
      
    case 'CommandSent':
      await handleCommandSent(detail);
      break;
      
    case 'StatusUpdate':
      await handleStatusUpdate(detail);
      break;
      
    default:
      console.log('Unhandled event type:', eventType);
  }
}

async function handleDevicesSynced(detail) {
  const { installation_id, device_count, entity_count, entities, timestamp } = detail;
  
  console.log(`Synced ${device_count} devices, ${entity_count} entities for ${installation_id}`);
  
  // Process entity state changes for automation triggers
  for (const entity of entities || []) {
    await checkEntityTriggers(installation_id, entity);
  }
  
  // Update installation stats
  await updateInstallationStats(installation_id, {
    last_sync: timestamp,
    device_count,
    entity_count
  });
}

async function handleInstallationRegistered(detail) {
  const { installation_id, timestamp } = detail;
  
  console.log(`New installation registered: ${installation_id}`);
  
  // Send welcome notification (if SNS is configured)
  if (NOTIFICATION_TOPIC_ARN) {
    await sendNotification(
      `New Home Assistant installation registered: ${installation_id}`,
      { installation_id, timestamp }
    );
  }
  
  // Initialize installation metrics
  await initializeInstallationMetrics(installation_id);
}

async function handleCommandSent(detail) {
  const { installation_id, action, entity_id, timestamp } = detail;
  
  console.log(`Command sent to ${installation_id}: ${action} on ${entity_id}`);
  
  // Log command for audit trail
  await logCommand(installation_id, action, entity_id, timestamp);
}

async function handleStatusUpdate(detail) {
  const { installation_id, entities, timestamp } = detail;
  
  console.log(`Status update from ${installation_id}: ${entities.length} entities`);
  
  // Process real-time entity updates
  for (const entity of entities || []) {
    await processEntityStatusUpdate(installation_id, entity, timestamp);
  }
}

async function checkEntityTriggers(installation_id, entity) {
  try {
    // Example automation triggers
    
    // 1. Security alerts
    if (entity.entity_id.includes('alarm') && entity.state === 'triggered') {
      console.log('🚨 SECURITY ALERT: Alarm triggered!', entity);
      
      await sendNotification(
        `🚨 SECURITY ALERT: ${entity.entity_id} triggered in installation ${installation_id}`,
        { installation_id, entity_id: entity.entity_id, state: entity.state }
      );
      
      // Emit high-priority alert event
      await eventBridge.send(new PutEventsCommand({
        Entries: [{
          Source: 'homeassistant.automation',
          DetailType: 'SecurityAlert',
          Detail: JSON.stringify({
            installation_id,
            entity_id: entity.entity_id,
            alert_type: 'alarm_triggered',
            timestamp: new Date().toISOString()
          }),
          EventBusName: EVENT_BUS_NAME
        }]
      }));
    }
    
    // 2. Environmental monitoring
    if (entity.entity_id.includes('temperature')) {
      const temp = parseFloat(entity.state);
      if (temp > 30 || temp < 5) { // Extreme temperatures
        console.log(`🌡️ Temperature alert: ${entity.entity_id} = ${temp}°C`);
        
        await sendNotification(
          `🌡️ Temperature Alert: ${entity.entity_id} = ${temp}°C`,
          { installation_id, entity_id: entity.entity_id, temperature: temp }
        );
      }
    }
    
    // 3. Energy monitoring
    if (entity.entity_id.includes('power') || entity.entity_id.includes('energy')) {
      const power = parseFloat(entity.state);
      if (power > 5000) { // High power consumption
        console.log(`⚡ High power consumption: ${entity.entity_id} = ${power}W`);
      }
    }
    
    // 4. Door/window sensors
    if (entity.device_class === 'door' || entity.device_class === 'window') {
      if (entity.state === 'open') {
        console.log(`🚪 Door/Window opened: ${entity.entity_id}`);
      }
    }
    
  } catch (error) {
    console.error('Error checking entity triggers:', error);
  }
}

async function updateInstallationStats(installation_id, stats) {
  try {
    const updateExpression = [];
    const expressionValues = {};
    
    Object.keys(stats).forEach(key => {
      updateExpression.push(`${key} = :${key}`);
      expressionValues[`:${key}`] = stats[key];
    });
    
    await docClient.send(new UpdateCommand({
      TableName: TABLE_NAME,
      Key: {
        PK: `INSTALL#${installation_id}`,
        SK: 'METADATA'
      },
      UpdateExpression: `SET ${updateExpression.join(', ')}`,
      ExpressionAttributeValues: expressionValues
    }));
    
  } catch (error) {
    console.error('Error updating installation stats:', error);
  }
}

async function initializeInstallationMetrics(installation_id) {
  try {
    // Create initial metrics record
    await docClient.send(new UpdateCommand({
      TableName: TABLE_NAME,
      Key: {
        PK: `INSTALL#${installation_id}`,
        SK: 'METRICS'
      },
      UpdateExpression: 'SET total_syncs = :zero, total_commands = :zero, created_at = :now',
      ExpressionAttributeValues: {
        ':zero': 0,
        ':now': new Date().toISOString()
      }
    }));
    
  } catch (error) {
    console.error('Error initializing metrics:', error);
  }
}

async function logCommand(installation_id, action, entity_id, timestamp) {
  try {
    // Update command counter
    await docClient.send(new UpdateCommand({
      TableName: TABLE_NAME,
      Key: {
        PK: `INSTALL#${installation_id}`,
        SK: 'METRICS'
      },
      UpdateExpression: 'ADD total_commands :inc SET last_command = :timestamp',
      ExpressionAttributeValues: {
        ':inc': 1,
        ':timestamp': timestamp
      }
    }));
    
  } catch (error) {
    console.error('Error logging command:', error);
  }
}

async function processEntityStatusUpdate(installation_id, entity, timestamp) {
  // This could be used for real-time dashboards, analytics, etc.
  console.log(`Entity ${entity.entity_id} updated: ${entity.state}`);
  
  // Example: Store in time-series data for analytics
  // You could extend this to write to CloudWatch, TimeStream, etc.
}

async function sendNotification(message, data) {
  if (!NOTIFICATION_TOPIC_ARN) {
    console.log('Notification (no SNS configured):', message);
    return;
  }
  
  try {
    await sns.send(new PublishCommand({
      TopicArn: NOTIFICATION_TOPIC_ARN,
      Message: JSON.stringify({ message, data }),
      Subject: 'Home Assistant Alert'
    }));
    
    console.log('Notification sent:', message);
  } catch (error) {
    console.error('Error sending notification:', error);
  }
}