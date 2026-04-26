# API Patterns: Gamma & CLOB Reference

## Endpoints

```
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"
```

---

## Gamma API: `/events/{event_id}`

**Request:**
```python
url = f"{GAMMA_BASE}/events/{event_id}"
req = Request(url, headers={"User-Agent": "poly-ui/1.0"})
```

**Response schema (relevant fields):**
```json
{
  "markets": [
    {
      "question": "Will the price of Bitcoin be less than $120K on Aug 12?",
      "clobTokenIds": "[\"0xabc...\", \"0xdef...\"]",   // JSON-encoded string
      "outcomePrices": "[\"0.75\", \"0.23\"]",           // JSON-encoded string
      "outcomes": "[\"Yes\", \"No\"]",                   // JSON-encoded string
      "closed": false,
      "resolved": false
    }
  ]
}
```

**Parsing contract:**
```python
tokens  = json.loads(m.get("clobTokenIds", "[]"))
prices  = json.loads(m.get("outcomePrices", "[]"))
outcomes = json.loads(m.get("outcomes", "[]"))

# Only keep valid Yes/No markets:
if len(tokens) != 2 or len(prices) != 2 or outcomes != ["Yes", "No"]:
    continue  # skip

# tokens[0] = Yes token, tokens[1] = No token
# prices[0] = Yes price, prices[1] = No price (static snapshot — use CLOB for live)
```

**Error cases:**
- `ev` is `None` or missing `"markets"` key → `raise RuntimeError("No markets found for event")`
- Individual market parse failure → `continue` (skip market, don't crash)

---

## CLOB API: `/price?token_id=...&side=buy`

**Request:**
```python
url = f"{CLOB_BASE}/price?token_id={token_id}&side={side}"
```

**Response — two valid shapes:**
```
# Shape 1: JSON object
{"price": 0.742}

# Shape 2: Raw float (plain text body)
0.742
```

**Parsing contract in `http_get_json()`:**
```python
try:
    return json.loads(data.decode("utf-8"))
except json.JSONDecodeError:
    s = data.decode("utf-8").strip()
    try:
        return float(s)          # handles raw float response
    except Exception:
        return None
```

**Downstream handling in `fetch_price()`:**
```python
if isinstance(j, dict):
    return float(j.get("price")) if j.get("price") is not None else None
if isinstance(j, (int, float)):
    return float(j)
return None
```

**Never assume a JSON response shape** — always handle both.

---

## CoinGecko: BTC Spot Price

```
url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
```

**Response:**
```json
{"bitcoin": {"usd": 118938.00}}
```

Timeout: 5s. Returns `None` on any failure (non-critical path).

---

## `http_get_json()` — Shared HTTP Utility

```python
def http_get_json(url, timeout=10):
    req = Request(url, headers={"User-Agent": "poly-ui/1.0"})
    with urlopen(req, timeout=timeout) as r:
        data = r.read()
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        s = data.decode("utf-8").strip()
        try:
            return float(s)
        except Exception:
            return None
```

**Key behaviors:**
- Raises `URLError`/`HTTPError` on network failure — callers must handle
- Returns `None` for unparseable non-JSON, non-float responses
- Zero external dependencies (stdlib only: `urllib.request`, `json`)

---

## Error Handling Contract

| Location | Failure Mode | Expected Behavior |
|----------|-------------|-------------------|
| `fetch_event_markets()` | Network error | Propagate exception → caught in `main()` |
| `fetch_event_markets()` | Bad market structure | `continue` — skip malformed markets |
| `fetch_price()` | Network error | Caller catches `URLError`/`HTTPError`, sets `yp = None` |
| `fetch_price()` | Returns None | UI displays `"  n/a "` for that bracket |
| `calculate_implied_bitcoin_price()` | Any exception | `return None` — graceful degradation |
| `fetch_additional_event_data()` | Any exception | `return []` — graceful degradation |
| AI API call | Any exception | `ai_state['analysis'] = f"AI unavailable: {str(e)[:30]}..."` |

**Solve, don't punt**: All foreseeable failures produce graceful degradation, not raw tracebacks to Claude.

---

## Rate Limiting & Timing

- CLOB prices: fetched per bracket per UI refresh cycle (every `interval` seconds, default 3s)
- Market data collection: every 25s (background thread)
- AI analysis: every 30s (background thread, uses pre-collected market data)
- BTC spot: every 60s (background thread)

No explicit rate limiting in the code — rely on natural timing. If 429s appear, increase `interval`.
