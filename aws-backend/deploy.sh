#!/bin/bash

# Home Assistant Cloud Backend - Deployment Script
# This script deploys the AWS infrastructure for the Home Assistant cloud integration

set -e

echo "🏠 Home Assistant Cloud Backend Deployment"
echo "========================================="

# Configuration
STAGE=${1:-dev}
REGION=${2:-us-east-1}

echo "📋 Deployment Configuration:"
echo "   Stage: $STAGE"
echo "   Region: $REGION"

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install and configure AWS CLI first."
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✅ AWS CLI configured"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18 or higher required. Current: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Validate serverless configuration
echo "🔍 Validating serverless configuration..."
npx serverless print --stage $STAGE --region $REGION > /dev/null

# Deploy to AWS
echo "🚀 Deploying to AWS..."
echo "   This may take 5-10 minutes..."

npx serverless deploy --stage $STAGE --region $REGION --verbose

# Get deployment information
echo "📊 Deployment Information:"
npx serverless info --stage $STAGE --region $REGION

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📋 Next Steps:"
echo "   1. Note the API Gateway URL from the output above"
echo "   2. Update your Home Assistant custom component const.py with this URL"
echo "   3. Test the endpoints using the test script: ./test-endpoints.sh $STAGE"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: npm run logs:register (or sync, webhook, events)"
echo "   Remove stack: npm run remove:$STAGE"
echo "   Redeploy: ./deploy.sh $STAGE $REGION"
echo ""
echo "📖 Documentation: See README.md for detailed usage instructions"