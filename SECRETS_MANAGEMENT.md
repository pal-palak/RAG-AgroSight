# 🔐 AgroSight Secrets Management Guide

## Overview

This guide explains how to securely manage API keys and sensitive credentials in AgroSight.

---

## ⚠️ Critical Security Rules

1. **NEVER commit `.env` to git** – It's already in `.gitignore`
2. **NEVER hardcode secrets in code** – Always use environment variables or secrets backend
3. **NEVER share `.env` files** – Keep them locally or use secrets management service
4. **ROTATE keys regularly** – Especially in production environments
5. **Use `.env.example`** – As template for required secrets

---

## 🚀 Local Development Setup

### Step 1: Create `.env` from template

```bash
cp .env.example .env
```

### Step 2: Fill in your API keys

Edit `.env` and replace placeholders with your actual keys:

```dotenv
MISTRAL_API_KEY=sk-xxxxx...
QDRANT_URL=https://your-instance.eu-west-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIs...
# ... other required keys
```

### Step 3: Verify setup

```bash
python -c "from app.utils.config import get_settings; s = get_settings(); print('✓ All secrets validated')"
```

---

## 🔧 Secrets Backend Options

### Option 1: Environment Variables (Default)

```bash
# Set directly in shell
export MISTRAL_API_KEY=sk-xxxxx
export QDRANT_URL=https://...

# Or load from .env
source .env
```

### Option 2: AWS Secrets Manager

**Setup:**
```bash
# Install AWS CLI
pip install boto3

# Set backend
export SECRETS_BACKEND=aws

# Configure AWS credentials
aws configure
```

**Store secrets:**
```bash
aws secretsmanager create-secret \
  --name agrosight/mistral-api-key \
  --secret-string "sk-xxxxx"

aws secretsmanager create-secret \
  --name agrosight/qdrant-api-key \
  --secret-string "eyJhbGciOiJ..."
```

### Option 3: HashiCorp Vault

**Setup:**
```bash
# Install hvac
pip install hvac

# Set backend
export SECRETS_BACKEND=vault
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=your-token
```

**Store secrets:**
```bash
vault kv put secret/agrosight \
  MISTRAL_API_KEY="sk-xxxxx" \
  QDRANT_API_KEY="eyJhbGciOiJ..."
```

### Option 4: Azure Key Vault

**Setup:**
```bash
# Install Azure SDK
pip install azure-identity azure-keyvault-secrets

# Set backend
export SECRETS_BACKEND=azure
export AZURE_KEYVAULT_URL=https://your-vault.vault.azure.net/
```

**Store secrets:**
```bash
az keyvault secret set \
  --vault-name agrosight \
  --name MISTRAL-API-KEY \
  --value "sk-xxxxx"
```

---

## 📋 Required Secrets

These secrets **must** be set for the application to start:

| Secret | Source | Purpose |
|--------|--------|---------|
| `MISTRAL_API_KEY` | [Mistral Console](https://console.mistral.ai/) | LLM API access |
| `QDRANT_URL` | [Qdrant Cloud](https://cloud.qdrant.io/) | Vector database URL |
| `QDRANT_API_KEY` | [Qdrant Cloud](https://cloud.qdrant.io/) | Vector database auth |

---

## 📝 Optional Secrets

These secrets enable additional features (application works without them):

| Secret | Source | Purpose |
|--------|--------|---------|
| `OPENWEATHER_API_KEY` | [OpenWeather](https://openweathermap.org/api) | Weather advisory |
| `DATA_GOV_API_KEY_1` | [Data.gov.in](https://data.gov.in/) | Government datasets |
| `AGMARKNET_API_KEY` | [Agmarknet](https://agmarknet.gov.in/) | Market prices |
| `USDA_NASS_API_KEY` | [USDA NASS](https://quickstats.nass.usda.gov/api/) | Crop statistics |
| `KAGGLE_KEY` | [Kaggle](https://kaggle.com/settings/account) | PlantVillage images |

---

## 🐳 Docker & Production

### Using Docker with environment variables

```dockerfile
# Dockerfile (secrets not included)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ /app/app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### Running with Docker Compose

```yaml
# docker-compose.yml
services:
  api:
    build: .
    environment:
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - QDRANT_URL=${QDRANT_URL}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      - SECRETS_BACKEND=env
    ports:
      - "8000:8000"
```

**Run with secrets from host:**
```bash
export $(cat .env | xargs)
docker-compose up
```

### Using AWS Secrets Manager in production

```yaml
# docker-compose.yml with AWS
services:
  api:
    build: .
    environment:
      - SECRETS_BACKEND=aws
      - AWS_REGION=us-east-1
    env_file:
      - .env.aws  # Contains AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

---

## 🚨 Troubleshooting

### Error: "Missing required secrets"

**Cause:** One or more required keys not set

**Solution:**
1. Check `.env` file exists: `ls -la .env`
2. Verify keys are filled in: `grep MISTRAL_API_KEY .env`
3. Reload environment: `source .env` or restart terminal

### Error: "AWS Secrets Manager error"

**Cause:** AWS credentials not configured or secret doesn't exist

**Solution:**
1. Configure AWS: `aws configure`
2. Verify credentials: `aws sts get-caller-identity`
3. Check secret exists: `aws secretsmanager describe-secret --secret-id agrosight/mistral-api-key`

### Error: "Vault connection failed"

**Cause:** Vault server unreachable or token invalid

**Solution:**
1. Check Vault running: `curl -k https://localhost:8200/v1/sys/health`
2. Verify token: `echo $VAULT_TOKEN`
3. Renew token if expired: `vault token renew`

---

## ✅ Security Checklist

- [ ] `.env` file created from `.env.example`
- [ ] All required secrets filled in `.env`
- [ ] `.env` in `.gitignore` (never commit)
- [ ] API keys rotated within last 90 days
- [ ] Different keys for dev/staging/prod
- [ ] Audit logging enabled for secret access
- [ ] Backup/recovery plan for lost secrets
- [ ] CI/CD secrets configured (GitHub Secrets, GitLab CI/CD Variables, etc.)

---

## 🔄 Rotating Secrets

### When to rotate:
- Monthly in development
- Quarterly in production
- Immediately if compromised

### Steps:
1. Generate new API key from service console
2. Update in secrets backend (AWS/Vault/etc.)
3. Update `.env` locally
4. Restart application
5. Verify connectivity
6. Delete old key from service console
7. Document rotation in audit log

---

## 📚 References

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Environment Variables Best Practices](https://12factor.net/config)
- [OWASP Secrets Management](https://owasp.org/www-community/Sensitive_Data_Exposure)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [HashiCorp Vault](https://www.vaultproject.io/docs)

---

## 📞 Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Review application logs: `tail -f logs/app.log`
3. Test secret retrieval: `python -c "import os; print(os.getenv('MISTRAL_API_KEY')[:5] + '...')"`
4. Open an issue with logs (never include actual secret values)
