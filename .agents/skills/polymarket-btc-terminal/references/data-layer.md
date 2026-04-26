# Data Layer Reference

## API Endpoints

- **Gamma API**: `https://gamma-api.polymarket.com` (Events and Markets)
- **CLOB API**: `https://clob.polymarket.com` (Live Orderbook Prices)
- **CoinGecko**: `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`

## Core Data Patterns

### Raw Float Handling
The Polymarket `/price` endpoint occasionally returns a raw number instead of a JSON object. The `http_get_json` function handles this transition:
```python
try:
    return json.loads(data.decode("utf-8"))
except json.JSONDecodeError:
    s = data.decode("utf-8").strip()
    return float(s)
```

### Event Synthesis
The data layer combines three distinct event types for prediction accuracy:
1. **37049** (Broad Ranges): e.g., $120k-$121k.
2. **36060** (Fine Ranges): e.g., $2k brackets.
3. **37057** (Reach/Dip): Volatility markers.

## Threading Safety

Data fetching must be non-blocking. Every data source uses its own daemon thread.
- **Locking**: All reads/writes to shared state dicts must be wrapped in `with state_lock:`.
- **Implementation**:
  ```python
  state_lock = threading.Lock()
  # In main loop:
  with state_lock:
      # read/write state
  # In async thread:
  with lock:
      # write state
  ```
- **States**: `market_state`, `ai_state`, `btc_state`.

## Error Handling
- Network failures in background threads must be caught and logged (e.g., `"BTC: Loading..."`).
- Failed threads must NOT update their `last_update` timestamp, forcing a retry on the next cycle.
