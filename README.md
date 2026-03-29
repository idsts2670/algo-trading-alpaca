# Alpaca Algo Trading Bot

**Alpaca Resources**


|                                   |                                                                                                                      |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Alpaca's Trading API website      | [https://alpaca.markets/algotrading](https://alpaca.markets/algotrading)                                             |
| `alpaca-py` Python SDK            | [https://alpaca.markets/sdks/python/](https://alpaca.markets/sdks/python/)                                           |
| Learn Articles                    | [https://alpaca.markets/learn](https://alpaca.markets/learn)                                                         |
| How to Open Start Paper Trading   | [https://alpaca.markets/learn/start-paper-trading](https://alpaca.markets/learn/start-paper-trading)                 |
| How to Open Live Account (Non-US) | [https://alpaca.markets/learn/live-trading-account-non-us](https://alpaca.markets/learn/live-trading-account-non-us) |


---

A serverless trading bot that runs the **LBR 3/10 Anti setup** (Linda Bradford Raschke) on the Magnificent 7 stocks, deployed on AWS Lambda and triggered daily at market open.

---

## How it works

```
CloudWatch cron (9:30 AM ET, Mon–Fri)
        │
        ▼
  Market open? ──No──▶ skip
        │
       Yes
        │
        ▼
  Scan Magnificent 7 (AAPL MSFT NVDA GOOGL AMZN META TSLA)
  For each symbol, run LBR Anti setup (6 rules):
    1. Enough daily bars (≥ 31)
    2. ADX(14) ≤ 32 or not rising       — avoid strong trends
    3. Price above EMA(20)              — long-only filter
    4. Signal line crossed zero upward  — trend change confirmed
    5. MACD pulled back to signal line  — pullback complete
    6. Histogram ticking up             — entry hook
        │
        ▼
  Equal-weight buy confirmed symbols
  Place ATR-based trailing stop on each position
  Save portfolio state → DynamoDB
```

Positions are rebalanced on every trigger. Symbols that no longer pass the Anti setup are sold; new signals are bought. The bot is **paper trading by default** — no real money until you explicitly switch.

---

## Architecture


| Component       | Service                                    |
| --------------- | ------------------------------------------ |
| Trigger         | CloudWatch Events (cron)                   |
| Runtime         | AWS Lambda (Python 3.12, 5 min timeout)    |
| Dependencies    | Lambda Layer (alpaca-py, pandas, numpy, …) |
| Portfolio state | DynamoDB                                   |
| Secrets         | AWS SSM Parameter Store                    |
| Broker API      | Alpaca Markets                             |
| IaC             | Serverless Framework v4                    |


---

## Project structure

```
├── main.py               # Lambda handler + LBR strategy
├── alpaca_broker.py      # Alpaca API wrapper
├── tests/                # Unit tests (pytest)
├── docs/
│   ├── PRE-DEPLOYMENT.md # AWS setup checklist (do this first)
│   └── DEPLOYMENT.md     # Step-by-step deploy guide
├── architecture/         # Mermaid diagrams
└── notebooks/            # Algorithm walkthrough (Jupyter)
```

---

## Quick start

**1. Read the checklist first**
`docs/PRE-DEPLOYMENT.md` — covers AWS account setup, IAM user, SSM credentials, and Serverless account. Do this before anything else.

**2. Deploy**
Follow `docs/DEPLOYMENT.md` step by step. The key commands:

```bash
uv sync                          # install Python deps
npm ci                           # install Serverless Framework
# build the Lambda layer (see DEPLOYMENT.md Step 5)
npx serverless deploy            # deploy to AWS
```

**3. Smoke test**

```bash
npx serverless invoke --function trading-bot --log
# expect: {"status": "skipped", "reason": "market_closed"} outside market hours
```

---

## Strategy: LBR 3/10 Anti setup

The 3/10 oscillator is `SMA(3) − SMA(10)` — a momentum indicator using **simple** moving averages (not EMA). The Anti setup catches minor countertrend moves within a larger trend using these rules:

- **No strong trend** — ADX(14) must be ≤ 32 or falling
- **Uptrend context** — price above EMA(20)
- **Trend change** — signal line (SMA-16 of the oscillator) crossed zero from below
- **Pullback** — oscillator retreats to signal line after making a new high
- **Hook** — histogram turns back up (entry timing)

Stops are placed at `entry − ATR(14) × 1.5`. Target is `entry + ATR(14) × 1.5` (1:1 R:R).

> Source: Linda Bradford Raschke, *Street Smarts* (1996) Ch. 9

---

## Switching to live trading

Update SSM with your live Alpaca keys, then set `ALPACA_PAPER: "False"` in `serverless.yml` and redeploy. See `docs/DEPLOYMENT.md` for details.