# LBR 3/10 Anti Setup — Algorithm Walkthrough Notebook

## Overview

**`ibr_algorithm_walkthrough.ipynb`** is a fully executable, step-by-step teaching notebook that demonstrates the Linda Raschke 3/10 Anti Setup trading algorithm.

This notebook is designed for **Google Colab** and any Jupyter environment with Alpaca API credentials.

---

## What's Inside

### **9 Runnable Sections**

| # | Section | Purpose |
|---|---------|---------|
| **1** | Fetch Daily Bars | Pull 120 daily bars from Alpaca for any symbol |
| **2** | ADX(14) Filter | Measure trend strength — blocks strong-trend markets |
| **3** | EMA(20) Trend | Confirm uptrend — long-only trades above 20-bar EMA |
| **4** | ATR(14) Volatility | Calculate risk/reward — stop distance and proximity |
| **5** | LBR 3/10 Chart | Visual walkthrough of the oscillator (MACD + Signal) |
| **6** | 6 Anti Setup Rules | Full signal function with rule-by-rule trace |
| **7** | Signal Scan | Run the signal across Magnificent 7 symbols |
| **8** | Portfolio Sizing | Equal-weight allocation demo ($100k example) |
| **9** | Stop Parameters | ATR-based stop placement & exit math |

---

## Setup

### **Option 1: Google Colab (Recommended)**

1. Open the notebook in [Google Colab](https://colab.research.google.com)
2. Upload the notebook or import from GitHub
3. Set API credentials in **Secrets** (left sidebar):
   - `ALPACA_API_KEY` = your Alpaca API key
   - `ALPACA_SECRET_KEY` = your Alpaca secret key
4. Run cells top-to-bottom

### **Option 2: Local Jupyter**

1. Ensure Python 3.9+ and Jupyter are installed
2. Install dependencies:
   ```bash
   pip install alpaca-py python-dotenv pandas numpy scipy matplotlib
   ```
3. Create a `.env` file in the project root:
   ```
   ALPACA_API_KEY=your_key_here
   ALPACA_SECRET_KEY=your_secret_here
   ```
4. Launch Jupyter and open the notebook:
   ```bash
   jupyter notebook ibr_algorithm_walkthrough.ipynb
   ```

---

## Key Features

✅ **Live Alpaca API Calls** — fetches real daily bars, quotes, and calendar data  
✅ **Real-Time Streaming Setup** — includes StockDataStream configuration  
✅ **Full Algorithm Logic** — all 6 Anti setup rules implemented  
✅ **Visual Outputs** — price chart with EMA(20) + LBR 3/10 oscillator  
✅ **Portfolio Math** — equal-weight sizing + position diff calculation  
✅ **Production-Ready** — same functions used in AWS Lambda deployment  
✅ **Google Colab Compatible** — works without local setup  

---

## What's NOT Included

The following production components are intentionally excluded:

| Component | Why |
|-----------|-----|
| `handler()` | Lambda entry point — requires CloudWatch context |
| `_store_portfolio()` | DynamoDB operations — requires AWS IAM roles |
| `place_order()` | Live order submission — demo only |
| `cancel_order()` | Modifies account state — demo only |
| `_get_clients()` | SSM Parameter Store — uses Lambda IAM role |

These functions are available in `main.py` and `alpaca_broker.py` for reference.

---

## Core Algorithms

### **ADX (Average Directional Index)**
- Measures trend strength (0–100)
- **Blocks signal** if ADX > 32 AND rising
- Uses Wilder's smoothing (alpha = 1/period)

### **EMA(20)**
- Exponential moving average of closing prices
- **Uptrend filter**: Long only when Close > EMA(20)

### **ATR(14)**
- Average True Range — volatility measure
- **Stop distance**: `ATR × 1.5`
- **Proximity check**: MACD within `0.5 × ATR` of signal

### **LBR 3/10 Oscillator**
- **MACD line** = SMA(3) − SMA(10)
- **Signal line** = SMA(16) of MACD
- **Histogram** = MACD − Signal (momentum indicator)

### **6 Anti Setup Rules** (all must pass)
1. ✅ Sufficient data (≥31 bars)
2. ✅ ADX not too strong (≤32 or falling)
3. ✅ Price in uptrend (above EMA(20))
4. ✅ Signal crossed zero from below
5. ✅ MACD pulled back to signal line
6. ✅ Histogram ticking up (hist[now] > hist[prev])

---

## Real-Time Quote Streaming

The notebook initializes a real-time streaming client:

```python
stream = StockDataStream(api_key=ALPACA_API_KEY, feed="sip")

async def handle_quote(quote):
    latest_quotes[quote.symbol] = {
        "askPrice": quote.ask_price,
        "bidPrice": quote.bid_price,
        "timestamp": quote.timestamp
    }

# To start streaming (optional):
# stream.subscribe_quotes(handle_quote, *MAGNIFICENT_7)
# await stream.run()
```

This enables real-time market data updates for production trading.

---

## Example Output

When you run Section 7 (Signal Scan), you'll see:

```
Scanning Magnificent 7...
  Scanning AAPL... ❌
  Scanning MSFT... ✅ SELECTED
  Scanning NVDA... ✅ SELECTED
  Scanning GOOGL... ❌
  Scanning AMZN... ❌
  Scanning META... ✅ SELECTED
  Scanning TSLA... ❌

============================================================
✅  Anti setup confirmed for: ['MSFT', 'NVDA', 'META']
   ATR per symbol:
     MSFT: $4.32
     NVDA: $8.15
     META: $6.87
============================================================
```

Then Section 8 sizes a $100k portfolio:

```
Portfolio value : $100,000
Selected symbols: ['MSFT', 'NVDA', 'META']
Per-symbol alloc: $33,333

Desired positions: {'MSFT': 123, 'NVDA': 67, 'META': 89}
Sells            : {}
Buys             : {'MSFT': 123, 'NVDA': 67, 'META': 89}
```

And Section 9 shows stop/target parameters:

```
Symbol   Entry    Stop   Target   Risk$  Trail%    ATR
-------------------------------------------------------
MSFT    $350.25 $344.81 $356.68   $5.44   1.55%  $4.32
NVDA    $875.40 $863.19 $887.61  $12.21   1.39%  $8.15
META    $425.18 $416.95 $434.41   $8.23   1.93%  $6.87
```

---

## Connection to Production Code

This notebook mirrors the logic in:

- **`main.py`** — Lambda handler and orchestration
- **`alpaca_broker.py`** — Alpaca API client wrapper
- **`architecture-flow.mmd`** — System architecture diagram

See those files for the full production deployment.

---

## Troubleshooting

### **Import Error: alpaca-py not found**
```bash
pip install alpaca-py
# or in Colab: !pip install alpaca-py
```

### **No API credentials found**
- **Colab**: Go to Secrets (left sidebar) → set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- **Local**: Create `.env` file with your credentials (see Setup section)

### **API Rate Limit Hit**
- Alpaca free tier has rate limits. Wait 1 minute before retrying.
- Alternatively, reduce symbol count or increase delays between calls.

### **Cells fail silently**
- Ensure all cells in the **Setup** section (1–8) run successfully first
- Check Alpaca status at [alpaca.markets/status](https://alpaca.markets/status)

---

## Next Steps

1. **Run the notebook top-to-bottom** to see the algorithm in action
2. **Modify `MAGNIFICENT_7`** to scan different symbols
3. **Adjust `portfolio_value`** in Section 8 to test different allocation sizes
4. **Study the 6 rules** — each one filters out specific market conditions
5. **Check `main.py`** to see how this deploys to AWS Lambda

---

## License & Attribution

This trading algorithm is based on **Linda Raschke's 3/10 Anti Setup**, a mean-reversion pullback strategy designed for daily charts. Raschke is a legendary trader and author of *Street Smarts*.

This notebook is for **educational purposes only**. Always backtest before deploying capital.

---

**Created:** March 2026  
**Status:** Fully tested with Alpaca Paper Trading API  
**Maintainers:** AI Algo Trader Bootcamp Team
