#!/usr/bin/env bash
# Deploy the Gemini CLI agent to Cloud Run (uses Vertex AI for both ADK and Gemini CLI).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-gemini-cli-adk}"

gcloud services enable run.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com \
  --project "$PROJECT_ID"

gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --memory 2Gi --cpu 2 --timeout 900 \
  --no-allow-unauthenticated \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION"

# The Cloud Run service account needs roles/aiplatform.user to call Gemini.
