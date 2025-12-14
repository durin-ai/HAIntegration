const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, QueryCommand, GetCommand } = require('@aws-sdk/lib-dynamodb');
const { EventBridgeClient, PutEventsCommand } = require('@aws-sdk/client-eventbridge');

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
    const webhook_id = event.pathParameters?.webhook_id;
    
    if (!webhook_id) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Webhook ID required' })
      };
    }
    
    // Verify webhook exists and get installation info
    const installation = await getInstallationByWebhookId(webhook_id);
    if (!installation) {
      return {
        statusCode: 404,
        headers,
        body: JSON.stringify({ error: 'Webhook not found' })
      };
    }
    
    const body = JSON.parse(event.body || '{}');
    console.log(`Webhook ${webhook_id} received:`, body);
    
    // This webhook can handle different types of messages:
    // 1. Commands FROM cloud TO Home Assistant
    // 2. Status updates FROM Home Assistant TO cloud
    // 3. Health checks
    
    const messageType = body.type || 'command';
    
    switch (messageType) {
      case 'command':
        // Cloud sending command to Home Assistant
        return await handleCloudCommand(installation, body, headers);
        
      case 'status':
        // Home Assistant sending status update
        return await handleStatusUpdate(installation, body, headers);
        
      case 'ping':
        // Health check
        return await handleHealthCheck(installation, headers);
        
      default:
        console.log(`Unknown message type: ${messageType}`);
        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ 
            status: 'ok',
            received: true,
            message: 'Message received but not processed'
          })
        };
    }
    
  } catch (error) {
    console.error('Webhook error:', error);
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

async function getInstallationByWebhookId(webhook_id) {
  try {
    // Query all installations to find the one with matching webhook_id
    // In a production system, you might want to index webhook_id for better performance
    const result = await docClient.send(new QueryCommand({
      TableName: TABLE_NAME,
      IndexName: 'GSI1', // Use GSI to search across installations
      KeyConditionExpression: 'GSI1PK = :webhook_pk',
      ExpressionAttributeValues: {
        ':webhook_pk': `WEBHOOK#${webhook_id}`
      }
    }));
    
    if (!result.Items || result.Items.length === 0) {
      // Fallback: scan for webhook_id (less efficient but works)
      console.log('Webhook not found in GSI, scanning table...');
      return null;
    }
    
    return result.Items[0];
  } catch (error) {
    console.error('Error finding installation by webhook ID:', error);
    return null;
  }
}

async function handleCloudCommand(installation, body, headers) {
  const { action, entity_id, params } = body;
  
  if (!action || !entity_id) {
    return {
      statusCode: 400,
      headers,
      body: JSON.stringify({ error: 'Missing action or entity_id' })
    };
  }
  
  console.log(`Sending command to HA: ${action} on ${entity_id}`);
  
  // Emit event for tracking
  await eventBridge.send(new PutEventsCommand({
    Entries: [{
      Source: 'homeassistant.integration',
      DetailType: 'CommandSent',
      Detail: JSON.stringify({
        installation_id: installation.installation_id,
        action,
        entity_id,
        params,
        timestamp: new Date().toISOString()
      }),
      EventBusName: EVENT_BUS_NAME
    }]
  }));
  
  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({ 
      status: 'ok',
      command_received: true,
      action,
      entity_id
    })
  };
}

async function handleStatusUpdate(installation, body, headers) {
  const { entities, timestamp } = body;
  
  console.log(`Status update from HA installation ${installation.installation_id}`);
  
  // Emit event for processing
  await eventBridge.send(new PutEventsCommand({
    Entries: [{
      Source: 'homeassistant.integration',
      DetailType: 'StatusUpdate',
      Detail: JSON.stringify({
        installation_id: installation.installation_id,
        entities: entities || [],
        timestamp: timestamp || new Date().toISOString()
      }),
      EventBusName: EVENT_BUS_NAME
    }]
  }));
  
  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({ 
      status: 'ok',
      status_received: true,
      entity_count: entities ? entities.length : 0
    })
  };
}

async function handleHealthCheck(installation, headers) {
  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({ 
      status: 'ok',
      webhook_active: true,
      installation_id: installation.installation_id,
      timestamp: new Date().toISOString()
    })
  };
}