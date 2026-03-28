# Pre-Deployment Checklist

Complete every item below **before** running any command in `DEPLOYMENT.md`.
Each section maps to a failure mode that will silently break the deploy or the live bot.

---

## 1. Local tooling

| # | Check | Command |
|---|-------|---------|
| 1.1 | uv is installed | `uv --version` → should print `0.x.x` |
| 1.2 | Python 3.12 is available to uv | `uv python list` → confirm `3.12.x` appears |
| 1.3 | Node.js is installed (required by Serverless) | `node --version` → `v18` or later |
| 1.4 | npm is installed | `npm --version` |
| 1.5 | AWS CLI is installed | `aws --version` |

---

## 2. AWS credentials and permissions

| # | Check | Command |
|---|-------|---------|
| 2.1 | AWS CLI is authenticated | `aws sts get-caller-identity` → prints your account ID |
| 2.2 | Active region is `us-east-1` | `aws configure get region` → `us-east-1` (or set with `aws configure`) |
| 2.3 | Your IAM identity can deploy CloudFormation | Needs `cloudformation:*`, `lambda:*`, `iam:*`, `s3:*`, `logs:*`, `ssm:GetParameter`, `dynamodb:*` |
| 2.4 | Your IAM identity can write SSM SecureString | `aws ssm put-parameter --name /test/check --value x --type SecureString && aws ssm delete-parameter --name /test/check` |

> **Minimum IAM policy for deployment:** The deploying identity needs broader permissions than the Lambda itself. If you are in an organisation account, confirm with your admin that CloudFormation stack creation is not blocked by an SCP.

---

## 3. Alpaca API keys

| # | Check | How |
|---|-------|-----|
| 3.1 | You have an Alpaca account | Sign up at alpaca.markets |
| 3.2 | Paper trading keys are generated | Dashboard → API Keys → Paper → generate key pair |
| 3.3 | Keys are stored in SSM under the exact parameter names below | See commands in Step 4 of `DEPLOYMENT.md` |

Required SSM parameter names (must match exactly — serverless.yml references these):

```
/alpaca/ALPACA_API_KEY
/alpaca/ALPACA_SECRET_KEY
```

Verify after storing:

```bash
aws ssm get-parameter --name /alpaca/ALPACA_API_KEY --with-decryption --query Parameter.Value
aws ssm get-parameter --name /alpaca/ALPACA_SECRET_KEY --with-decryption --query Parameter.Value
```

Both should return your key values, not an error.

---

## 4. Repository state

| # | Check | Command |
|---|-------|---------|
| 4.1 | No hardcoded API keys or secrets | `grep -rn "ALPACA_API_KEY\s*=\s*[\"'][A-Z0-9]" .` → no output |
| 4.2 | `uv.lock` is committed | `git status uv.lock` → `nothing to commit` |
| 4.3 | `layer/python/` does not exist yet (clean build) | `ls layer/python` → `No such file or directory` is correct |
| 4.4 | `requirements-lambda.txt` does not exist yet | `ls requirements-lambda.txt` → not found is correct |
| 4.5 | `package.json` and `package-lock.json` are committed | `git status package*.json` → nothing to commit |
| 4.6 | `node_modules/` is not committed | `git ls-files node_modules` → no output |

---

## 5. Python environment

| # | Check | Command |
|---|-------|---------|
| 5.1 | `uv sync` completes without errors | `uv sync` |
| 5.2 | All tests pass locally | `uv run pytest tests/ -v` |
| 5.3 | No import errors in main modules | `uv run python -c "import main; import alpaca_broker"` → no output |

All 9 tests in `tests/test_macd.py` and `tests/test_alpaca.py` must pass before deploy.

---

## 6. Serverless Framework

| # | Check | Command |
|---|-------|---------|
| 6.1 | `npm ci` completes cleanly | `npm ci` (uses pinned `package-lock.json`) |
| 6.2 | Serverless version matches `package.json` | `npx serverless --version` → should print `4.x.x` |
| 6.3 | Serverless can resolve SSM parameters | `npx serverless print` → should print the resolved config without `${ssm:...}` placeholders |

> `npx serverless print` is a dry-run that validates your `serverless.yml` and resolves all variable references including SSM. If the SSM parameters from section 3 are missing, this command will fail here — before any infrastructure is touched.

---

## 7. Lambda layer build prerequisites

| # | Check | Why |
|---|-------|-----|
| 7.1 | You are on a machine with internet access | `uv pip install` will download Linux wheels from PyPI |
| 7.2 | Disk has at least 500 MB free | The layer directory unpacks to ~300 MB |
| 7.3 | You are **not** inside a Python virtual env that overrides `--python-platform` | Run `deactivate` if a venv is active before building the layer |

---

## 8. Live trading gate (skip if staying on paper)

Only relevant when you intend to switch `ALPACA_PAPER` to `"False"`.

| # | Check |
|---|-------|
| 8.1 | Live trading keys are provisioned in your Alpaca account (requires identity verification) |
| 8.2 | You have reviewed the trailing stop percentage (`TRAILING_STOP_PERCENTAGE = 4.75` in `main.py`) and accept the risk |
| 8.3 | You have tested the full paper flow and seen at least one successful trade cycle in CloudWatch Logs |
| 8.4 | You understand that the Lambda fires every weekday at 9:30 AM ET and will place real orders automatically |

---

## Quick pre-flight sequence

Run these four commands in order. If all pass, you are ready for `DEPLOYMENT.md`:

```bash
# 1. Confirm AWS identity and region
aws sts get-caller-identity
aws configure get region

# 2. Confirm SSM keys are in place
aws ssm get-parameter --name /alpaca/ALPACA_API_KEY --with-decryption --query Parameter.Value
aws ssm get-parameter --name /alpaca/ALPACA_SECRET_KEY --with-decryption --query Parameter.Value

# 3. Run tests
uv run pytest tests/ -v

# 4. Dry-run serverless config resolution
npm ci && npx serverless print
```

All four must succeed with no errors before proceeding to `DEPLOYMENT.md`.
