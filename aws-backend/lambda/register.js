const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, GetCommand } = require('@aws-sdk/lib-dynamodb');
const { EventBridgeClient, PutEventsCommand } = require('@aws-sdk/client-eventbridge');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');

const ddbClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(ddbClient);
const eventBridge = new EventBridgeClient({});

const TABLE_NAME = process.env.TABLE_NAME;
const EVENT_BUS_NAME = process.env.EVENT_BUS_NAME;
const API_GATEWAY_URL = process.env.API_GATEWAY_URL;

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
    console.log('Registration request:', event.body);
    const body = JSON.parse(event.body);
    const { api_key } = body;
    
    if (!api_key) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'API key is required' })
      };
    }
    
    // Validate API key (implement your validation logic)
    const isValid = await validateApiKey(api_key);
    if (!isValid) {
      return {
        statusCode: 401,
        headers,
        body: JSON.stringify({ error: 'Invalid API key' })
      };
    }
    
    // Generate unique IDs
    const installation_id = uuidv4();
    const webhook_id = uuidv4();
    const hashed_key = crypto.createHash('sha256').update(api_key).digest('hex');
    
    // Store installation
    await docClient.send(new PutCommand({
      TableName: TABLE_NAME,
      Item: {
        PK: `INSTALL#${installation_id}`,
        SK: 'METADATA',
        installation_id,
        api_key_hash: hashed_key,
        webhook_id,
        created_at: new Date().toISOString(),
        last_sync: null,
        status: 'active'
      }
    }));
    
    console.log(`Created installation: ${installation_id}`);
    
    // Emit registration event
    await eventBridge.send(new PutEventsCommand({
      Entries: [{
        Source: 'homeassistant.integration',
        DetailType: 'InstallationRegistered',
        Detail: JSON.stringify({
          installation_id,
          timestamp: new Date().toISOString()
        }),
        EventBusName: EVENT_BUS_NAME
      }]
    }));
    
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        installation_id,
        webhook_id,
        webhook_url: `${API_GATEWAY_URL}/webhook/${webhook_id}`
      })
    };
    
  } catch (error) {
    console.error('Registration error:', error);
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

async function validateApiKey(api_key) {
  // TODO: Implement your API key validation logic
  // For now, accept any non-empty key
  // In production, check against your user database
  return api_key && api_key.length > 10;
}