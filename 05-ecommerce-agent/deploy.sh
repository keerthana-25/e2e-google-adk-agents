#!/usr/bin/env bash
# Deploy to Google Cloud: Cloud SQL (Postgres) + MCP Toolbox on Cloud Run + agent backend on Cloud Run.
# Assumes the Cloud SQL instance/database already exist and db/init.sql was loaded into it.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SQL_CONNECTION="${SQL_CONNECTION:?set SQL_CONNECTION=project:region:instance}"
DB_PASSWORD="${DB_PASSWORD:?set DB_PASSWORD}"
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:?set GOOGLE_CLIENT_ID (OAuth client for Google Sign-In)}"

gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com \
  aiplatform.googleapis.com cloudbuild.googleapis.com --project "$PROJECT_ID"

# 1. tools.yaml as a secret (env vars inside it are filled in by toolbox at startup)
gcloud secrets create shop-tools --data-file=mcp-toolbox/tools.yaml --project "$PROJECT_ID" \
  || gcloud secrets versions add shop-tools --data-file=mcp-toolbox/tools.yaml --project "$PROJECT_ID"

# 2. MCP Toolbox (private, only the backend's service account can call it)
gcloud run deploy shop-toolbox \
  --image us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest \
  --region "$REGION" --project "$PROJECT_ID" \
  --set-secrets "/app/tools.yaml=shop-tools:latest" \
  --args="--config=/app/tools.yaml","--address=0.0.0.0","--port=8080" \
  --add-cloudsql-instances "$SQL_CONNECTION" \
  --set-env-vars "DB_HOST=/cloudsql/$SQL_CONNECTION,DB_PORT=5432,DB_NAME=shopdb,DB_USER=postgres,DB_PASSWORD=$DB_PASSWORD" \
  --no-allow-unauthenticated

TOOLBOX_URL=$(gcloud run services describe shop-toolbox --region "$REGION" --project "$PROJECT_ID" --format 'value(status.url)')

# 3. Agent backend
gcloud run deploy shop-agent \
  --source . --region "$REGION" --project "$PROJECT_ID" \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,MCP_TOOLBOX_URL=$TOOLBOX_URL,TOOLBOX_USE_ID_TOKEN=true,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID" \
  --allow-unauthenticated   # app-level auth: /chat verifies the Google ID token

# 4. Let the backend's service account invoke the toolbox:
#    gcloud run services add-iam-policy-binding shop-toolbox --region $REGION \
#      --member serviceAccount:<backend-sa> --role roles/run.invoker
#    and roles/aiplatform.user on the project for Gemini.
