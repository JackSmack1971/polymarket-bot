# Thread Patterns Reference

## Table of Contents
1. [Standard Async Function Template](#1-standard-async-function-template)
2. [Adding a New Thread (4th Source)](#2-adding-a-new-thread-4th-source)
3. [Binance Funding Rate Example](#3-binance-funding-rate-example)
4. [Lock-Safe State Wrapper](#4-lock-safe-state-wrapper)
5. [Graceful Degradation Pattern](#5-graceful-degradation-pattern)
6. [Laggy UI Fixes](#6-laggy-ui-fixes)

---

## 1. Standard Async Function Template

Every async function follows this exact shape — `updating = False` at the very end, inside the function:

```python
def update_source_async(source_state):
    try:
        # Do I/O here
        data = fetch_something()
        source_state['data'] = data
        source_state['last_update'] = time.time()
    except Exception as e:
        source_state['data'] = f"Unavailable: {str(e)[:40]}"
    finally:
        source_state['updating'] = False   # ← ALWAYS last, ALWAYS in the thread
```

---

## 2. Adding a New Thread (4th Source)

**Step 1 — State dict** (near the other state dicts in `main()`):
```python
new_state = {
    'data': None,
    'last_update': 0,
    'updating': False
}
```

**Step 2 — Async function** (near the other async functions, ~line 338):
```python
def update_new_source_async(new_state):
    try:
        result = fetch_new_source()
        new_state['data'] = result
        new_state['last_update'] = time.time()
    except Exception as e:
        new_state['data'] = f"Unavailable: {str(e)[:40]}"
    finally:
        new_state['updating'] = False
```

**Step 3 — Main loop trigger** (add after the btc_state block, ~line 717):
```python
NEW_INTERVAL = 45  # seconds
if (current_time - new_state['last_update'] >= NEW_INTERVAL
        and not new_state['updating']):
    new_state['updating'] = True
    threading.Thread(
        target=update_new_source_async,
        args=(new_state,),
        daemon=True
    ).start()
```

**Step 4 — Draw section** (bottom of the draw block):
```python
if new_state['data'] is not None:
    stdscr.addstr(row, col, f"New Source: {new_state['data']}")
```

---

## 3. Binance Funding Rate Example

Full implementation of a funding rate thread:

```python
funding_state = {'rate': None, 'symbol': None, 'last_update': 0, 'updating': False}

def update_funding_rate_async(funding_state):
    url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
    try:
        data = http_get_json(url)
        if data and 'lastFundingRate' in data:
            funding_state['rate'] = float(data['lastFundingRate']) * 100  # as %
            funding_state['symbol'] = data.get('symbol', 'BTCUSDT')
        funding_state['last_update'] = time.time()
    except Exception as e:
        funding_state['rate'] = None
    finally:
        funding_state['updating'] = False

# In main loop (interval = 45s):
if (current_time - funding_state['last_update'] >= 45
        and not funding_state['updating']):
    funding_state['updating'] = True
    threading.Thread(target=update_funding_rate_async,
                     args=(funding_state,), daemon=True).start()

# In draw section (next to BTC price line):
if funding_state['rate'] is not None:
    fr_text = f"Funding: {funding_state['rate']:+.4f}%"
    stdscr.addstr(bottom_row, col + 30, fr_text)
```

---

## 4. Lock-Safe State Wrapper

Drop-in thread safety for all three (or four) state dicts:

```python
# At module level, near the top of main():
state_lock = threading.Lock()

# In every async function, replace direct assignment with:
with state_lock:
    market_state['current_data'] = current_data
    market_state['last_update'] = time.time()
with state_lock:
    market_state['updating'] = False

# In the main loop, reads don't strictly need the lock for simple types,
# but for safety wrap the snapshot:
with state_lock:
    current_analysis = ai_state['analysis']
    current_model = ai_state.get('model', 'AI')
```

---

## 5. Graceful Degradation Pattern

Each async function must handle its own failure so other threads continue:

```python
def update_ai_analysis_async(current_data, previous_data, ai_state):
    try:
        # ... all API calls and processing ...
        ai_state['analysis'] = response.output_text.strip()
        ai_state['last_update'] = time.time()
    except Exception as e:
        ai_state['analysis'] = f"AI unavailable: {str(e)[:30]}..."
        # Do NOT update last_update — forces retry next cycle
    finally:
        ai_state['updating'] = False
```

For the draw section, always check for None / error strings:
```python
if ai_state['analysis'].startswith("AI unavailable"):
    # Show in dimmed color or with warning prefix
    stdscr.addstr(row, col, ai_state['analysis'], curses.A_DIM)
```

---

## 6. Laggy UI Fixes

**Option A — Increase intervals** (simplest):
```python
MARKET_INTERVAL = 30   # was 25
AI_INTERVAL     = 45   # was 30
BTC_INTERVAL    = 90   # was 60
```

**Option B — Increase main loop timeout**:
```python
stdscr.timeout(5000)   # was 3000 — check threads every 5s instead of 3s
```

**Option C — Sub-second responsiveness** (advanced, for fast keypress response):
```python
stdscr.nodelay(True)
# Replace stdscr.timeout() approach with:
time.sleep(0.05)   # 50ms sleep — acceptable ONLY with nodelay(True)
```
Use Option C only if the user explicitly needs fast keypress response; the timeout approach is simpler and preferred.
