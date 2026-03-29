# Troubleshooting: KeyError: 'datetime' & API Errors

## The Error

```
KeyError: 'datetime'
```

This happens in **Section 1 (Fetch Data)** when trying to access `df["datetime"]`. 

**Root cause:** `price_data` is empty, meaning `get_price_history()` returned no bars from Alpaca.

---

## **Immediate Fix: What to Check**

### **1. Credentials Set? ✅**

**For Google Colab:**
- Click **Secrets** (🔑 icon, left sidebar)
- Verify these are set:
  - `ALPACA_API_KEY` = your actual key
  - `ALPACA_SECRET_KEY` = your actual secret
- Don't include quotes or extra spaces

**For Local Jupyter:**
- Create `.env` file in project root:
  ```
  ALPACA_API_KEY=your_key_here
  ALPACA_SECRET_KEY=your_secret_here
  ```
- Don't commit `.env` to git (it's in `.gitignore`)

### **2. Are credentials valid? ✅**

Verify by running this cell:
```python
print(f"API Key: {ALPACA_API_KEY}")
print(f"Secret Key: {ALPACA_SECRET_KEY}")
```

If either shows `None`, credentials are not loaded.

### **3. Market Hours? ✅**

Alpaca only has data during market hours. Try:
- **During market:** Monday-Friday, 9:30 AM - 4:00 PM ET
- **After hours:** Still works (uses EOD data from previous day)
- **Weekends/Holidays:** No data available

Check if today is a trading day:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")
now = datetime.now(NY_TZ)
print(f"Current time: {now}")
print(f"Day of week: {now.strftime('%A')}")
```

### **4. Internet connection? ✅**

Test connectivity:
```python
import requests
response = requests.get("https://alpaca.markets", timeout=5)
print(f"Connection: {response.status_code}")
```

---

## **How to Debug the API Call**

Add this diagnostic cell after the imports:

```python
# Test API connectivity
print("Testing Alpaca API...")
print(f"  API Key loaded: {bool(ALPACA_API_KEY)}")
print(f"  Secret Key loaded: {bool(ALPACA_SECRET_KEY)}")
print(f"  Client initialized: {bool(stock_historical_data_client)}")

# Try a simple request
try:
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    NY_TZ = ZoneInfo("America/New_York")
    today = datetime.now(NY_TZ).date()
    start = today - timedelta(days=5)
    
    req = StockBarsRequest(
        symbol_or_symbols="AAPL",
        timeframe=TimeFrame.Day,
        start=start,
    )
    response = stock_historical_data_client.get_stock_bars(req)
    
    if "AAPL" in response:
        print(f"✅ API working! Got {len(response['AAPL'])} bars for AAPL")
    else:
        print(f"❌ AAPL not in response. Keys: {list(response.keys())}")
        
except Exception as e:
    print(f"❌ API Error: {e}")
    import traceback
    traceback.print_exc()
```

---

## **Common Issues & Solutions**

### **Issue: `PermissionError` or `401 Unauthorized`**
```
alpaca.trading.client.APIError: (401, {'code': 40110001, 'message': 'Unauthorized'})
```

**Solution:**
- Credentials are wrong
- Check Alpaca dashboard for correct keys
- Regenerate keys if needed
- Make sure you're using **paper trading** keys (not live)

---

### **Issue: `TypeError: StockDataStream.__init__() missing 1 required positional argument`**
```
TypeError: StockDataStream.__init__() missing 1 required positional argument: 'secret_key'
```

**Solution:**
- ✅ **FIXED** in updated notebook (Cell 6)
- `StockDataStream` now includes `secret_key` parameter

---

### **Issue: Empty response but no error**
```
KeyError: 'datetime'  (means price_data is [])
```

**Solution:**
Check if symbol is valid:
```python
# Try a test fetch with debugging
import traceback

def get_price_history_debug(symbol):
    try:
        today = datetime.now(NY_TZ).date()
        start = today - timedelta(days=180)
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
        )
        print(f"Request: {symbol} from {start} to {today}")
        response = stock_historical_data_client.get_stock_bars(req)
        print(f"Response keys: {list(response.keys())}")
        
        bars_data = response[symbol] if symbol in response else []
        print(f"Bars fetched: {len(bars_data)}")
        return bars_data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return []

# Test with AAPL
bars = get_price_history_debug("AAPL")
```

---

### **Issue: `AttributeError: 'NoneType' object has no attribute 'get'`**

Means credentials not loaded:
```python
# Check explicitly
if ALPACA_API_KEY is None:
    print("❌ ALPACA_API_KEY is None!")
    if "google.colab" in sys.modules:
        print("   → Set in Colab Secrets (left sidebar 🔑)")
    else:
        print("   → Check .env file exists and has ALPACA_API_KEY=...")
```

---

## **Updated Cells Handle Errors Better**

The updated notebook now includes:

### **Cell 6 (Streaming Setup):**
```python
try:
    stream = StockDataStream(...)
except Exception as e:
    print(f"⚠️  Streaming setup warning: {e}")
    print("   Data fetching will work fine without streaming.")
```

### **Cell 10 (Section 1 - Fetch Data):**
```python
if not price_data:
    print("\n❌ ERROR: No data returned from Alpaca API")
    print("\nPossible causes:")
    print("  1. API credentials not set...")
    # ... helpful guidance
```

---

## **Quick Troubleshooting Checklist**

- [ ] Credentials set in `.env` or Colab Secrets?
- [ ] Credentials are **paper trading** keys (not live)?
- [ ] Internet connection working?
- [ ] During market hours (Mon-Fri, 9:30 AM - 4:00 PM ET)?
- [ ] Symbol is valid (e.g., "AAPL", "MSFT", not "XYZ")?
- [ ] Run the debug cell above to see exact API response?

---

## **Get Help**

If you've checked everything:

1. **Copy the debug output from the cell above**
2. **Share:**
   - The exact error message
   - Your `.env` or Colab Secrets setup
   - The time/date you ran it
   - Your local timezone

3. **Verify Alpaca status:**
   - Go to https://alpaca.markets/status
   - Check if APIs are working

---

## **Update Applied**

The notebook has been updated with:
- ✅ Better error messages in `get_price_history()`
- ✅ Fixed `StockDataStream` secret_key parameter
- ✅ Comprehensive error handling in Section 1
- ✅ Diagnostic output when data fetch fails

**Re-run the notebook from the beginning after updating.**

