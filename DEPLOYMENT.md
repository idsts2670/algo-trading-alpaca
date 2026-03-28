# Deployment Guide

## Prerequisites

### Step 1 — Install uv

```bash
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2 — Install Serverless Framework

```bash
npm ci
```

## Deploy

### Step 3 — Install project dependencies

```bash
uv sync
```

### Step 4 — Store Alpaca credentials in SSM

```bash
aws ssm put-parameter \
  --name /alpaca/ALPACA_API_KEY \
  --value "YOUR_ALPACA_KEY_ID" \
  --type SecureString

aws ssm put-parameter \
  --name /alpaca/ALPACA_SECRET_KEY \
  --value "YOUR_ALPACA_SECRET" \
  --type SecureString
```

Get your keys from alpaca.markets → Dashboard → API Keys.
For paper trading, use the paper environment key pair.

### Step 5 — Build the Lambda layer

```bash
uv export --no-dev --format requirements-txt -o requirements-lambda.txt

uv pip install \
  -r requirements-lambda.txt \
  --target ./layer/python \
  --python-platform linux \
  --python 3.12
```

`--python-platform linux` cross-compiles binary wheels for Amazon Linux 2.
Run this before every `serverless deploy`.

### Step 6 — Deploy

```bash
serverless deploy
```

### Step 7 — Smoke test (paper trading)

```bash
serverless invoke --function trading-bot --log
```

Confirm in CloudWatch Logs:

- No auth errors or import errors
- `"Market is closed — skipping run."` fires outside market hours
- MACD signal scores logged for all 7 symbols during market hours

## Switch to live trading

Update SSM with live keys:

```bash
aws ssm put-parameter \
  --name /alpaca/ALPACA_API_KEY \
  --value "YOUR_LIVE_KEY_ID" \
  --type SecureString --overwrite

aws ssm put-parameter \
  --name /alpaca/ALPACA_SECRET_KEY \
  --value "YOUR_LIVE_SECRET" \
  --type SecureString --overwrite
```

Then in `serverless.yml` change:

```yaml
ALPACA_PAPER: "False"
```

Redeploy with `serverless deploy`.