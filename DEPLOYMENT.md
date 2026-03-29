# Deployment Guide

## Prerequisites

### Step 1 — Install uv

```bash
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2 — Install Serverless Framework dependencies

```bash
npm ci
```

This installs the pinned Serverless Framework version from `package-lock.json`. Do not use `npm install -g serverless` — that installs an unpinned global version and bypasses the lock file.

## Deploy

### Step 3 — Install project dependencies

```bash
uv sync
```

Do not activate a virtual environment manually. `uv` manages `.venv` internally and all `uv run` commands use it automatically.

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

> **Parameter names must match exactly.** `serverless.yml` references `/alpaca/ALPACA_API_KEY` and `/alpaca/ALPACA_SECRET_KEY`. Any typo here will cause the deploy to fail at the SSM resolution step.

### Step 5 — Build the Lambda layer

AWS Lambda enforces a **250 MB unzipped size limit** on layers. Several packages in this project's dependency tree would exceed that limit if bundled naively:

- `boto3` / `botocore` / `s3transfer` — already pre-installed in the Lambda Python 3.12 runtime; bundling them wastes ~80 MB
- `llvmlite` — a 128 MB LLVM compiler backend pulled in by `pandas-ta` for optional JIT acceleration; not needed in a Lambda

Run the following commands to build a correctly sized layer. **Run this before every `serverless deploy`**, and always start with a clean `layer/python/` directory.

```bash
# 1. Clear any previous layer build
find layer/python -mindepth 1 -delete 2>/dev/null; echo "layer/python cleared"

# 2. Export dependencies without hashes (required for reliable line-by-line filtering)
uv export --no-dev --no-hashes --format requirements-txt -o requirements-lambda.txt

# 3. Remove packages already present in the Lambda runtime or not needed at runtime
grep -vE "^(boto3|botocore|s3transfer|numba|llvmlite)==" requirements-lambda.txt \
  > requirements-lambda-layer.txt

# 4. Install Linux wheels into the layer target directory
uv pip install \
  -r requirements-lambda-layer.txt \
  --target ./layer/python \
  --python-platform linux \
  --python 3.12

# 5. Remove numba/llvmlite if pip re-installed them as transitive dependencies
find layer/python/numba   -mindepth 1 -delete 2>/dev/null; rmdir layer/python/numba   2>/dev/null || true
find layer/python/llvmlite -mindepth 1 -delete 2>/dev/null; rmdir layer/python/llvmlite 2>/dev/null || true
```

Verify the final layer size is under 250 MB before deploying:

```bash
du -sh layer/python
```

Expected output: roughly `115M layer/python`. If it reads 250 MB or more, do not proceed — re-check that steps 3–5 ran without errors.

> **Why `--no-hashes`?** `uv export` by default produces a multi-line hash-pinned format where each package spans several lines. `grep` only removes the first line of a multi-line entry, leaving behind orphaned `--hash=sha256:...` lines that break the subsequent `uv pip install`. The `--no-hashes` flag produces a clean single-line-per-package format that filters correctly.

> **Why delete numba/llvmlite after install?** `pandas-ta` declares `numba` as a dependency, so `uv pip install` pulls it in regardless of the filtered requirements file. Deleting them post-install is safe — `pandas-ta` uses `numba` only for optional JIT acceleration; all MACD calculations work without it.

### Step 6 — Log in to Serverless Framework

Serverless Framework v4 requires a free account at [app.serverless.com](https://app.serverless.com). Run this once — it opens a browser to authenticate and saves a token locally:

```bash
npx serverless login
```

You only need to do this once per machine. Your `org` name from the dashboard is already set in `serverless.yml`.

### Step 7 — Deploy

```bash
npx serverless deploy
```

A successful deploy prints output similar to:

```
✔ Service deployed to stack algo-trading-alpaca-dev (103s)
functions:
  trading-bot: algo-trading-alpaca-dev-trading-bot (23 kB)
layers:
  alpacaDeps: arn:aws:lambda:us-east-2:xxxxxxxxxxxx:layer:alpacaDeps:1
```

The function package should be **under 50 kB** — it contains only `main.py` and `alpaca_broker.py`. If you see several MB, the `package.patterns` exclusions in `serverless.yml` are not taking effect.

> **Common deploy errors:**
>
> | Error | Cause | Fix |
> |-------|-------|-----|
> | `Unzipped size must be smaller than 262144000 bytes` on the **layer** | `llvmlite` or `boto3` still in layer | Re-run Step 5 and confirm `du -sh layer/python` is ~115 MB |
> | `Function code combined with layers exceeds 262144000 bytes` | `node_modules` or `.venv` bundled into the function zip | Confirm `package.patterns` in `serverless.yml` includes exclusions for `!node_modules/**`, `!.venv/**`, etc. |
> | `InvalidClientTokenId` | AWS credentials missing or stale | Re-run `aws configure` |
> | `Parameter /alpaca/... not found` | SSM parameter name mismatch or not yet created | Re-run Step 4 with exact parameter names |

### Step 8 — Smoke test (paper trading)

```bash
npx serverless invoke --function trading-bot --log
```

Confirm in CloudWatch Logs:

- No auth errors or import errors
- `"Market is closed — skipping run."` fires outside market hours and on weekends
- MACD signal scores logged for all 7 symbols during market hours or weekday extended sessions

## Redeploying

Every time you change `main.py`, `alpaca_broker.py`, or `serverless.yml`, redeploy with:

```bash
npx serverless deploy
```

Every time you update Python dependencies (`pyproject.toml`), rebuild the layer first (Step 5), then redeploy.

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

Redeploy with `npx serverless deploy`.
