const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, BatchWriteCommand, GetCommand, UpdateCommand } = require('@aws-sdk/lib-dynamodb');
const { EventBridgeClient, PutEventsCommand } = require('@aws-sdk/client-eventbridge');
const { IoTDataPlaneClient, PublishCommand } = require('@aws-sdk/client-iot-data-plane');

const ddbClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(ddbClient);
const eventBridge = new EventBridgeClient({});
const iotData = new IoTDataPlaneClient({});

const TABLE_NAME = process.env.TABLE_NAME;
const EVENT_BUS_NAME = process.env.EVENT_BUS_NAME;

exports.handler = async (event) => {
  console.log('MQTT message received:', JSON.stringify(event, null, 2));
  
  try {
    // AWS IoT Core triggers Lambda with the MQTT message
    const topic = event.topic;
    const payload = typeof event.payload === 'string' ? 
      JSON.parse(event.payload) : event.payload;
    
    // Route based on topic pattern
    if (topic.includes('/register')) {
      return await handleRegistration(payload, topic);
    } else if (topic.includes('/sync')) {
      return await handleSync(payload, topic);
    } else if (topic.includes('/status')) {
      return await handleStatus(payload, topic);
    } else if (topic.includes('/commands')) {
      return await handleCommand(payload, topic);
    }
    
    return { statusCode: 200, message: 'Message processed' };
    
  } catch (error) {
    console.error('MQTT processing error:', error);
    return { statusCode: 500, error: error.message };
  }
};

async function handleRegistration(payload, topic) {
  const { installation_id, timestamp } = payload;
  
  console.log(`Registration from installation: ${installation_id}`);
  
  try {
    // Store installation metadata
    await docClient.send(new PutCommand({
      TableName: TABLE_NAME,
      Item: {
        PK: `INSTALL#${installation_id}`,
        SK: 'METADATA',
        installation_id,
        created_at: new Date().toISOString(),
        last_seen: new Date().toISOString(),
        status: 'active',
        mqtt_topic_prefix: `durin/ha/${installation_id}`
      }
    }));
    
    // Emit registration event
    await eventBridge.send(new PutEventsCommand({
      Entries: [{
        Source: 'durin.mqtt',
        DetailType: 'InstallationRegistered',
        Detail: JSON.stringify({
          installation_id,
          timestamp: new Date().toISOString()
        }),
        EventBusName: EVENT_BUS_NAME
      }]
    }));
    
    // Publish acknowledgment back to the installation
    const ackTopic = `durin/ha/${installation_id}/ack`;
    await iotData.send(new PublishCommand({
      topic: ackTopic,
      payload: JSON.stringify({
        type: 'registration_ack',
        installation_id,
        status: 'success',
        timestamp: new Date().toISOString()
      }),
      qos: 1
    }));
    
    console.log(`Registration successful for ${installation_id}`);
    return { statusCode: 200, message: 'Registration successful' };
    
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
}

async function handleSync(payload, topic) {
  const { installation_id, devices, timestamp } = payload;
  
  console.log(`Sync from ${installation_id}: ${devices.length} devices`);
  
  try {
    const writeRequests = [];
    const changedEntities = [];
    
    // Process devices
    for (const device of devices) {
      // Store device
      writeRequests.push({
        PutRequest: {
          Item: {
            PK: `INSTALL#${installation_id}`,
            SK: `DEVICE#${device.device_id}`,
            device_id: device.device_id,
            name: device.name,
            manufacturer: device.manufacturer,
            model: device.model,
            entities: device.entities.map(e => e.entity_id),
            updated_at: new Date().toISOString()
          }
        }
      });
      
      // Store entities
      for (const entity of device.entities || []) {
        writeRequests.push({
          PutRequest: {
            Item: {
              PK: `INSTALL#${installation_id}`,
              SK: `ENTITY#${entity.entity_id}`,
              GSI1PK: `ENTITY#${entity.entity_id}`,
              GSI1SK: `INSTALL#${installation_id}`,
              entity_id: entity.entity_id,
              device_id: device.device_id,
              name: entity.name,
              device_class: entity.device_class,
              state: entity.state,
              attributes: entity.attributes,
              updated_at: new Date().toISOString()
            }
          }
        });
        
        changedEntities.push({
          entity_id: entity.entity_id,
          state: entity.state,
          device_id: device.device_id
        });
      }
    }
    
    // Write in batches of 25
    for (let i = 0; i < writeRequests.length; i += 25) {
      const batch = writeRequests.slice(i, i + 25);
      await docClient.send(new BatchWriteCommand({
        RequestItems: {
          [TABLE_NAME]: batch
        }
      }));
    }
    
    // Update last sync time
    await docClient.send(new UpdateCommand({
      TableName: TABLE_NAME,
      Key: {
        PK: `INSTALL#${installation_id}`,
        SK: 'METADATA'
      },
      UpdateExpression: 'SET last_sync = :timestamp, last_seen = :timestamp',
      ExpressionAttributeValues: {
        ':timestamp': new Date().toISOString()
      }
    }));
    
    // Emit sync event
    await eventBridge.send(new PutEventsCommand({
      Entries: [{
        Source: 'durin.mqtt',
        DetailType: 'DevicesSynced',
        Detail: JSON.stringify({
          installation_id,
          device_count: devices.length,
          entity_count: changedEntities.length,
          entities: changedEntities,
          timestamp: new Date().toISOString()
        }),
        EventBusName: EVENT_BUS_NAME
      }]
    }));
    
    console.log(`Synced ${devices.length} devices, ${changedEntities.length} entities`);
    return { statusCode: 200, message: 'Sync successful' };
    
  } catch (error) {
    console.error('Sync error:', error);
    throw error;
  }
}

async function handleStatus(payload, topic) {
  const { entity_id, state, attributes, timestamp } = payload;
  
  console.log(`Status update for ${entity_id}: ${state}`);
  
  try {
    // Extract installation_id from topic
    const topicParts = topic.split('/');
    const installation_id = topicParts[2]; // durin/ha/{installation_id}/status
    
    // Update entity state
    await docClient.send(new UpdateCommand({
      TableName: TABLE_NAME,
      Key: {
        PK: `INSTALL#${installation_id}`,
        SK: `ENTITY#${entity_id}`
      },
      UpdateExpression: 'SET #state = :state, attributes = :attrs, updated_at = :timestamp',
      ExpressionAttributeNames: {
        '#state': 'state'
      },
      ExpressionAttributeValues: {
        ':state': state,
        ':attrs': attributes,
        ':timestamp': new Date().toISOString()
      }
    }));
    
    // Emit status update event
    await eventBridge.send(new PutEventsCommand({
      Entries: [{
        Source: 'durin.mqtt',
        DetailType: 'StatusUpdate',
        Detail: JSON.stringify({
          installation_id,
          entity_id,
          state,
          attributes,
          timestamp: new Date().toISOString()
        }),
        EventBusName: EVENT_BUS_NAME
      }]
    }));
    
    return { statusCode: 200, message: 'Status updated' };
    
  } catch (error) {
    console.error('Status update error:', error);
    throw error;
  }
}

async function handleCommand(payload, topic) {
  const { type, action, entity_id, params } = payload;
  
  console.log(`Command received: ${action} on ${entity_id}`);
  
  try {
    // Extract installation_id from topic
    const topicParts = topic.split('/');
    const installation_id = topicParts[2];
    
    // Log command for audit
    await eventBridge.send(new PutEventsCommand({
      Entries: [{
        Source: 'durin.mqtt',
        DetailType: 'CommandReceived',
        Detail: JSON.stringify({
          installation_id,
          action,
          entity_id,
          params,
          timestamp: new Date().toISOString()
        }),
        EventBusName: EVENT_BUS_NAME
      }]
    }));
    
    return { statusCode: 200, message: 'Command logged' };
    
  } catch (error) {
    console.error('Command handling error:', error);
    throw error;
  }
}
