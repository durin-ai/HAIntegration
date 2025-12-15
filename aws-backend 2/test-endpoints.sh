#!/bin/bash

# Home Assistant Cloud Backend - Test Script
# Tests the deployed endpoints to verify functionality

set -e

STAGE=${1:-dev}
REGION=${2:-us-east-1}

echo "🧪 Testing Home Assistant Cloud Backend"
echo "======================================"
echo "Stage: $STAGE"
echo "Region: $REGION"
echo ""

# Get API Gateway URL from serverless output
echo "🔍 Getting API Gateway URL..."
API_URL=$(npx serverless info --stage $STAGE --region $REGION | grep "endpoint:" | awk '{print $2}')

if [ -z "$API_URL" ]; then
    echo "❌ Could not find API Gateway URL. Make sure the stack is deployed."
    exit 1
fi

echo "✅ API Gateway URL: $API_URL"
echo ""

# Test 1: Registration endpoint
echo "🧪 Test 1: Registration Endpoint"
echo "================================"

REGISTRATION_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$API_URL/ha/register" \
    -H "Content-Type: application/json" \
    -d '{"api_key": "test-key-12345678901234567890"}')

HTTP_CODE=$(echo "$REGISTRATION_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REGISTRATION_RESPONSE" | head -n -1)

echo "Response Code: $HTTP_CODE"
echo "Response Body: $RESPONSE_BODY"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Registration test passed"
    
    # Extract installation_id and webhook_id for further tests
    INSTALLATION_ID=$(echo "$RESPONSE_BODY" | grep -o '"installation_id":"[^"]*"' | cut -d'"' -f4)
    WEBHOOK_ID=$(echo "$RESPONSE_BODY" | grep -o '"webhook_id":"[^"]*"' | cut -d'"' -f4)
    
    echo "   Installation ID: $INSTALLATION_ID"
    echo "   Webhook ID: $WEBHOOK_ID"
else
    echo "❌ Registration test failed"
    echo ""
    exit 1
fi
echo ""

# Test 2: Sync endpoint
echo "🧪 Test 2: Sync Endpoint"
echo "========================"

SYNC_PAYLOAD='{
  "installation_id": "'$INSTALLATION_ID'",
  "devices": [
    {
      "device_id": "test-device-1",
      "name": "Test Light Switch",
      "manufacturer": "Test Corp",
      "model": "Model X",
      "entities": [
        {
          "entity_id": "light.test_light",
          "name": "Test Light",
          "device_class": "light",
          "state": "on",
          "attributes": {"brightness": 255, "color": "white"}
        },
        {
          "entity_id": "switch.test_switch",
          "name": "Test Switch", 
          "device_class": "switch",
          "state": "off",
          "attributes": {}
        }
      ]
    }
  ]
}'

SYNC_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$API_URL/ha/sync" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer test-key-12345678901234567890" \
    -d "$SYNC_PAYLOAD")

HTTP_CODE=$(echo "$SYNC_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SYNC_RESPONSE" | head -n -1)

echo "Response Code: $HTTP_CODE"
echo "Response Body: $RESPONSE_BODY"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Sync test passed"
else
    echo "❌ Sync test failed"
fi
echo ""

# Test 3: Webhook endpoint
echo "🧪 Test 3: Webhook Endpoint"
echo "==========================="

WEBHOOK_PAYLOAD='{
  "type": "command",
  "action": "turn_on",
  "entity_id": "light.test_light",
  "params": {"brightness": 128}
}'

WEBHOOK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$API_URL/webhook/$WEBHOOK_ID" \
    -H "Content-Type: application/json" \
    -d "$WEBHOOK_PAYLOAD")

HTTP_CODE=$(echo "$WEBHOOK_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$WEBHOOK_RESPONSE" | head -n -1)

echo "Response Code: $HTTP_CODE"
echo "Response Body: $RESPONSE_BODY"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Webhook test passed"
else
    echo "❌ Webhook test failed"
fi
echo ""

# Test 4: Health check
echo "🧪 Test 4: Webhook Health Check"
echo "==============================="

HEALTH_PAYLOAD='{"type": "ping"}'

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$API_URL/webhook/$WEBHOOK_ID" \
    -H "Content-Type: application/json" \
    -d "$HEALTH_PAYLOAD")

HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

echo "Response Code: $HTTP_CODE"
echo "Response Body: $RESPONSE_BODY"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check test passed"
else
    echo "❌ Health check test failed"
fi
echo ""

# Test 5: Invalid webhook
echo "🧪 Test 5: Invalid Webhook Test"
echo "==============================="

INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$API_URL/webhook/invalid-webhook-id" \
    -H "Content-Type: application/json" \
    -d '{"type": "ping"}')

HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -n1)

echo "Response Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "404" ]; then
    echo "✅ Invalid webhook test passed (correctly returned 404)"
else
    echo "❌ Invalid webhook test failed (should return 404)"
fi
echo ""

echo "🎉 Testing Complete!"
echo ""
echo "📊 Summary:"
echo "   API Gateway URL: $API_URL"
echo "   Installation ID: $INSTALLATION_ID"
echo "   Webhook ID: $WEBHOOK_ID"
echo ""
echo "💡 Next Steps:"
echo "   1. Use the API Gateway URL in your Home Assistant integration"
echo "   2. Use a real API key (not the test key) for production"
echo "   3. Monitor CloudWatch logs for any issues"
echo ""
echo "🔧 Monitoring Commands:"
echo "   npm run logs:register   # Registration function logs"
echo "   npm run logs:sync       # Sync function logs" 
echo "   npm run logs:webhook    # Webhook function logs"
echo "   npm run logs:events     # Event processor logs"