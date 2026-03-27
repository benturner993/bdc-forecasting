# Deploy to Azure Container Apps (New Subscription)

This guide shows how to deploy this Flask app to a brand new Azure subscription using:

- Azure Container Registry (ACR)
- Azure Container Apps (ACA)
- Log Analytics workspace

It is written as a copy/paste runbook.

## 1) Prerequisites

- Azure subscription with permission to create resources
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed
- Docker is not required locally if you use `az acr build` (recommended below)

## 2) Sign in and select subscription

```bash
az login
az account list --output table
az account set --subscription "<SUBSCRIPTION_ID_OR_NAME>"
```

Register providers and install the ACA extension:

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az extension add --name containerapp --upgrade
```

## 3) Set deployment variables

Run this once in your terminal (edit values if needed):

```bash
LOCATION="uksouth"
RESOURCE_GROUP="rg-bpc-forecasting"
ENV_NAME="acae-bpc-forecasting"
APP_NAME="aca-bpc-forecasting"
WORKSPACE_NAME="law-bpc-forecasting"

# Must be globally unique, lowercase letters/numbers only.
SUFFIX=$(openssl rand -hex 3)
ACR_NAME="acrbpc${SUFFIX}"

IMAGE_NAME="bpc-forecasting"
IMAGE_TAG="v1"
```

## 4) Confirm container files exist

This repo now includes both:

- `Dockerfile`
- `.dockerignore`

No manual creation is required. If you changed either file, validate locally first:

```bash
docker build -t bpc-forecasting:local .
docker run --rm -p 5000:5000 bpc-forecasting:local
```

Then open [http://localhost:5000](http://localhost:5000).

## 5) Create Azure resources

```bash
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"

az monitor log-analytics workspace create \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --location "$LOCATION"
```

Get Log Analytics IDs for ACA environment creation:

```bash
LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --query customerId -o tsv)

LOG_ANALYTICS_WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --query primarySharedKey -o tsv)
```

Create Container Apps Environment:

```bash
az containerapp env create \
  --name "$ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --logs-workspace-id "$LOG_ANALYTICS_WORKSPACE_ID" \
  --logs-workspace-key "$LOG_ANALYTICS_WORKSPACE_KEY"
```

Create ACR:

```bash
az acr create \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Basic \
  --admin-enabled true
```

## 6) Build and push the image to ACR

From the repo root (`bpc-forecasting`):

```bash
az acr build \
  --registry "$ACR_NAME" \
  --image "$IMAGE_NAME:$IMAGE_TAG" \
  .
```

Get ACR credentials for ACA pull:

```bash
ACR_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
```

## 7) Create the Container App

```bash
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_USERNAME" \
  --registry-password "$ACR_PASSWORD" \
  --target-port 5000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi
```

Get the live URL:

```bash
APP_FQDN=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "https://$APP_FQDN"
```

## 8) Verify deployment

```bash
curl -I "https://$APP_FQDN/"
```

Open in browser:

- `https://<fqdn>/`
- `https://<fqdn>/headlines`

## 9) Redeploy updates

For each new release:

```bash
IMAGE_TAG="v2"

az acr build \
  --registry "$ACR_NAME" \
  --image "$IMAGE_NAME:$IMAGE_TAG" \
  .

az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG"
```

## 10) Useful operations

Show app status:

```bash
az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --output table
```

Stream logs:

```bash
az containerapp logs show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --follow
```

Scale settings update:

```bash
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --min-replicas 1 \
  --max-replicas 5
```

## 11) Troubleshooting quick checks

- If container fails to start, confirm:
  - app binds to `0.0.0.0:5000`
  - `--target-port 5000` matches container port
- If image pull fails:
  - verify `ACR_USERNAME`, `ACR_PASSWORD`, and `ACR_SERVER`
- If startup is slow/fails due memory:
  - increase memory to `4.0Gi` and retry

## 12) Clean up (optional)

Delete everything created by this guide:

```bash
az group delete --name "$RESOURCE_GROUP" --yes --no-wait
```