const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, BatchWriteCommand, GetCommand, UpdateCommand } = require('@aws-sdk/lib-dynamodb');
const { EventBridgeClient, PutEventsCommand } = require('@aws-sdk/client-eventbridge');
const crypto = require('crypto');

const ddbClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(ddbClient);
const eventBridge = new EventBridgeClient({});

const TABLE_NAME = process.env.TABLE_NAME;
const EVENT_BUS_NAME = process.env.EVENT_BUS_NAME;

exports.handler = async (event) => {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
  };

  // Handle CORS preflight
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: ''
    };
  }

  try {
    console.log('Sync request body:', event.body);
    const body = JSON.parse(event.body);
    const { installation_id, devices } = body;
    
    if (!installation_id || !devices) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Missing required fields: installation_id and devices' })
      };
    }
    
    // Authenticate
    const authHeader = event.headers.Authorization || event.headers.authorization;
    const isAuthorized = await verifyAuth(authHeader, installation_id);
    
    if (!isAuthorized) {
      return {
        statusCode: 401,
        headers,
        body: JSON.stringify({ error: 'Unauthorized' })
      };
    }
    
    const timestamp = new Date().toISOString();
    const changedEntities = [];
    
    // Batch write devices and entities
    const writeRequests = [];
    
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
            updated_at: timestamp
          }
        }
      });
      
      // Store entities
      for (const entity of device.entities || []) {
        const entityItem = {
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
          updated_at: timestamp
        };
        
        writeRequests.push({
          PutRequest: { Item: entityItem }
        });
        
        changedEntities.push({
          entity_id: entity.entity_id,
          state: entity.state,
          device_id: device.device_id
        });
      }
    }
    
    console.log(`Processing ${writeRequests.length} items in batches`);
    
    // Write in batches of 25 (DynamoDB limit)
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
      UpdateExpression: 'SET last_sync = :timestamp',
      ExpressionAttributeValues: {
        ':timestamp': timestamp
      }
    }));
    
    console.log(`Synced ${devices.length} devices, ${changedEntities.length} entities`);
    
    // Emit sync event to EventBridge
    await eventBridge.send(new PutEventsCommand({
      Entries: [{
        Source: 'homeassistant.integration',
        DetailType: 'DevicesSynced',
        Detail: JSON.stringify({
          installation_id,
          device_count: devices.length,
          entity_count: changedEntities.length,
          entities: changedEntities,
          timestamp
        }),
        EventBusName: EVENT_BUS_NAME
      }]
    }));
    
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        synced_devices: devices.length,
        synced_entities: changedEntities.length,
        timestamp
      })
    };
    
  } catch (error) {
    console.error('Sync error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ 
        error: 'Internal server error',
        message: error.message 
      })
    };
  }
};

async function verifyAuth(authHeader, installation_id) {
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return false;
  }
  
  const api_key = authHeader.substring(7);
  const hashed_key = crypto.createHash('sha256').update(api_key).digest('hex');
  
  try {
    const result = await docClient.send(new GetCommand({
      TableName: TABLE_NAME,
      Key: {
        PK: `INSTALL#${installation_id}`,
        SK: 'METADATA'
      }
    }));
    
    return result.Item && result.Item.api_key_hash === hashed_key;
  } catch (error) {
    console.error('Auth verification error:', error);
    return false;
  }
}