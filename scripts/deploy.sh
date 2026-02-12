#!/bin/bash

# Deployment Script for Movement Voice Agent [Jason]
# Production Grade CI/CD Pipeline Template

set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
# --- CONFIG ---
SERVICE_NAME="core-voice-agent"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "🚀 Initiating Professional Deployment sequence..."

# 1. Build Container
echo "🛠️  Building Docker Image..."
gcloud builds submit --tag ${IMAGE_NAME} .

# 2. Deploy to Cloud Run
echo "📦 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"

echo "✅ Mission Success. Agent Jason is LIVE."
echo "🔗 Service URL: $(gcloud run services describe ${SERVICE_NAME} --format='value(status.url)' --region ${REGION})"
