#!/bin/bash
echo "🚀 Initializing Movement Voice Demo Deployment..."

# 1. Interactive Auth (Required due to expired token)
echo "🔑 Authenticating with Google Cloud..."
gcloud auth login

# 2. Set Context
echo "📡 Setting project context..."
gcloud config set project mineral-anchor-486222-a5

# 3. Deploy
echo "☁️ Deploying to Cloud Run (US-Central1)..."
cd demo-site
gcloud run deploy movement-voice-demo \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --quiet

echo "✅ Deployment Complete! Share the URL above."
