# Zeta IMA — Teams App Deployment Guide

## Prerequisites

- Azure subscription with an active **Azure Bot Service** registration
- Your web app deployed to a public domain (e.g. `zeta-ima.azurewebsites.net`)
- Node 18+ and Python 3.11+ locally
- [Teams Admin Center](https://admin.teams.microsoft.com) access (or permission to sideload apps)

---

## Step 1 — Register the Bot (Azure Bot Service)

1. Go to [portal.azure.com](https://portal.azure.com) → **Create a resource** → search **Azure Bot**
2. Fill in:
   - **Bot handle**: `zeta-ima-bot`
   - **Subscription + Resource Group**: your existing ones
   - **Pricing tier**: F0 (free) is fine for dev
   - **Microsoft App ID**: choose **Create new Microsoft App ID**
3. Click **Review + Create**
4. After creation, go to **Configuration** → note your **Microsoft App ID**
5. Go to **Configuration** → **Manage Password** → create a new **Client Secret** → save it
6. Under **Channels** → **Microsoft Teams** → Enable → Save

---

## Step 2 — Configure Environment Variables

Copy `.env.template` to `.env` in the project root and fill in:

```bash
# Bot identity
MICROSOFT_APP_ID=<your-bot-app-id>
MICROSOFT_APP_PASSWORD=<your-bot-client-secret>

# Azure AD (for Graph API proactive messaging)
AZ_TENANT_ID=<your-tenant-id>
AZ_CLIENT_ID=<same-as-MICROSOFT_APP_ID>
AZ_CLIENT_SECRET=<same-as-MICROSOFT_APP_PASSWORD>

# Azure Key Vault (for API key encryption)
AZ_KEY_VAULT_URL=https://<your-vault-name>.vault.azure.net
AZ_KEY_VAULT_SECRET_NAME=zeta-vault-key

# Teams broadcast channel (where approved outputs are posted)
TEAMS_TEAM_ID=<team-id>
TEAMS_BROADCAST_CHANNEL_ID=19:xxxx@thread.tacv2

# Your deployed frontend URL
FRONTEND_URL=https://<your-domain>
```

> **Finding your Teams channel ID**: In Teams, right-click the channel → **Get link to channel**. The URL contains the channel ID after `channel/`.

---

## Step 3 — Generate the Vault Fernet Key

Run once before first deploy. This key encrypts all API keys stored by the vault.

```bash
python - <<'EOF'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
EOF
```

Store this value as a secret named `zeta-vault-key` in your Azure Key Vault:

```bash
az keyvault secret set \
  --vault-name <your-vault-name> \
  --name zeta-vault-key \
  --value "<fernet-key-here>"
```

---

## Step 4 — Deploy the Backend

### Option A — Azure Container Apps (recommended)

```bash
# Build and push Docker image
docker build -t zetaima-backend .
az acr create --resource-group <rg> --name zetaimaacr --sku Basic
az acr login --name zetaimaacr
docker tag zetaima-backend zetaimaacr.azurecr.io/zetaima-backend:latest
docker push zetaimaacr.azurecr.io/zetaima-backend:latest

# Deploy
az containerapp create \
  --name zeta-ima-api \
  --resource-group <rg> \
  --environment <your-container-app-env> \
  --image zetaimaacr.azurecr.io/zetaima-backend:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars @.env
```

### Option B — Local dev tunnel (testing only)

```bash
# Install ngrok: https://ngrok.com
ngrok http 8000
# Copy the HTTPS URL — use it as your bot messaging endpoint
```

### Set the bot messaging endpoint

In Azure Bot Service → **Configuration** → **Messaging endpoint**:
```
https://<your-domain>/api/messages
```

---

## Step 5 — Deploy the Frontend

```bash
cd frontend
npm install
npm run build

# Option A — Vercel (fastest)
npx vercel --prod

# Option B — Azure Static Web Apps
az staticwebapp create \
  --name zeta-ima-frontend \
  --resource-group <rg> \
  --source . \
  --location eastus2 \
  --branch main \
  --app-location /frontend \
  --output-location .next

# Option C — serve from same Container App (add Next.js to Dockerfile)
```

Update `FRONTEND_URL` in your backend env to the deployed frontend URL.

---

## Step 6 — Seed Brand Memory (Optional)

If you have existing approved copy, seed Qdrant before launch:

```bash
# Edit brand_seeds/approved_copy.jsonl (see example file)
python scripts/seed_brand_memory.py --file brand_seeds/approved_copy.jsonl
```

---

## Step 7 — Package the Teams App

Edit `teams/manifest.json` — replace every `${{...}}` placeholder:

| Placeholder | Replace with |
|---|---|
| `${{MICROSOFT_APP_ID}}` | Your Bot App ID (from Step 1) |
| `${{YOUR_DOMAIN}}` | Your deployed frontend domain (no `https://`) |

Then create the zip:

```bash
cd teams
zip -r ZetaIMA.zip manifest.json color.png outline.png
```

> **Icon requirements**:
> - `color.png` — 192×192 px, full color, PNG
> - `outline.png` — 32×32 px, transparent background, white/outline only, PNG
>
> Use any design tool (Figma, Canva) to create these. A simple lightning bolt icon works well.

---

## Step 8 — Install in Teams

### Option A — Admin Center (org-wide)

1. Go to [Teams Admin Center](https://admin.teams.microsoft.com) → **Teams apps** → **Manage apps**
2. Click **Upload new app** → upload `ZetaIMA.zip`
3. Find "Zeta IMA" in the list → set **Status** to **Allowed**
4. Optionally: **Setup policies** → **Global** → **Add apps** → pin Zeta IMA to the sidebar

### Option B — Personal sideload (testing / individual)

1. In Teams: **Apps** (left sidebar) → **Manage your apps** → **Upload an app**
2. Select **Upload a custom app** → choose `ZetaIMA.zip`
3. Click **Add** on the install dialog

---

## Step 9 — Verify

After install, in Teams:

1. **DM the bot**: `@Zeta IMA write a LinkedIn post about our new product launch`
   - Expect: draft card with Approve/Reject buttons
2. **Approve the draft**: click Approve
   - Expect: confirmation card + message posted to your broadcast channel
3. **Personal tab**: click the Zeta IMA icon in the left rail → Chat tab loads
   - Expect: web app loads at `https://<your-domain>/chat` inside Teams frame
4. **File upload**: DM the bot and attach a PDF
   - Expect: "Ingesting document…" → knowledge base updated
5. **Settings**: open the Settings tab → add your Jira API key → Save
   - Expect: green ✓ appears on the Jira card

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Bot doesn't respond | Check messaging endpoint URL in Azure Bot → must be `https://` (not http) |
| "Unauthorized" in bot | Verify `MICROSOFT_APP_ID` + `MICROSOFT_APP_PASSWORD` match bot registration |
| Tabs show blank page | Check `validDomains` in manifest.json includes your domain without `https://` |
| Vault errors on startup | Ensure Managed Identity or `AZ_CLIENT_ID/SECRET` has **Key Vault Secrets User** role |
| Qdrant connection error | Check `docker compose up -d` is running; Qdrant port 6333 is accessible |
| Redis timeout | Verify Redis is running: `redis-cli ping` → should return `PONG` |
| "App not found" in Teams | Re-zip manifest + icons; manifest `id` must match your Bot App ID exactly |

---

## Local Development

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Start backend
pip install -r zeta_ima/requirements.txt
uvicorn zeta_ima.api.app:app --reload --port 8000

# 3. Start frontend
cd frontend && npm install && npm run dev

# 4. Tunnel for Teams bot testing
ngrok http 8000
# Set ngrok URL as messaging endpoint in Azure Bot Service

# 5. Open frontend
open http://localhost:3000
```
