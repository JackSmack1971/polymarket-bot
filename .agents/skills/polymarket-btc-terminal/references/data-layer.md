# Data Layer Reference

## API Endpoints

| API | Base URL | Purpose |
|---|---|---|
| Gamma | `https://gamma-api.polymarket.com` | Event metadata, market structure |
| CLOB | `https://clob.polymarket.com` | Live yes/no token prices |
| CoinGecko | `https://api.coingecko.com/api/v3` | Real BTC/USD price |

## Core HTTP Helper

```python
def http_get_json(url, timeout=10):
    req = Request(url, headers={"User-Agent": "poly-ui/1.0"})
    with urlopen(req, timeout=timeout) as r:
        data = r.read()
    # Handles both JSON and raw float responses (CLOB /price quirk)
```

## Fetching Event Markets

```python
def fetch_event_markets(event_id):
    # GET /events/{event_id}
    # Returns list of bracket dicts:
    # {bracket: str, yes_token: str, no_token: str}
    # Sorted: <X first, between ranges second, >X last
```

Sort key logic:
- `"will the price of bitcoin be less"` → `(0, s)`
- `"between"` → `(1, s)`
- `"greater"` → `(2, s)`

## Fetching Live Prices

```python
def fetch_price(token_id, side="buy"):
    # GET /price?token_id={token_id}&side={side}
    # Returns float or None
    # Handles: raw float response OR {"price": float} JSON
```

Called for both `yes_token` and `no_token` of each bracket to get live market prices.

## Fetching Real BTC Price

```python
def fetch_btc_price():
    # GET /simple/price?ids=bitcoin&vs_currencies=usd
    # Returns float (USD) or None
    # Timeout: 5s (shorter than default 10s)
```

## Event IDs (hardcoded)

| Variable | Event ID | Type | Bracket size |
|---|---|---|---|
| Primary (CLI arg `-e`) | 37049 | Broad ranges | ~$3-4k each |
| Fine ranges | 36060 | Fine ranges | ~$2k each |
| Reach/Dip | 37057 | Volatility | Boolean reach/dip |

Events 36060 and 37057 are hardcoded inside `main()`. Only the primary event ID comes from CLI.

## Market Data Format for AI

```python
def format_market_data_for_ai(brackets, event_id):
    # Returns:
    {
        "event_id": int,
        "timestamp": str,
        "markets": [
            {
                "bracket": str,
                "yes_price": float,
                "no_price": float,
                "implied_yes_prob": float,  # yes_price (since ~= probability)
            }, ...
        ]
    }
```

## Adding a New Event

1. Add `fetch_event_markets(NEW_EVENT_ID)` call in `main()` near the existing event fetches
2. Add a new section in the market table render loop with `stdscr.addstr(row, 0, "Event XXXXX (Label):", ...)`
3. Add the new event's data to `format_market_data_for_ai()` output
4. Update the system prompt in `update_ai_analysis_async()` to describe the new event's weight/purpose

## Sparkline Data

Each bracket dict in the `brackets` list gets a `history` key appended during the render loop:
```python
bracket.setdefault('history', []).append(current_yes_price)
bracket['history'] = bracket['history'][-hist:]  # hist = CLI arg, default 30
```

Rendered inline using block characters: `█` scaled by probability value.

## Error Handling Pattern

All async fetch functions follow this pattern:
```python
def update_X_async(state):
    try:
        # ... fetch and update state ...
        state['data'] = result
        state['last_update'] = time.time()
    except Exception:
        pass          # silent fail — UI shows stale data
    state['updating'] = False  # ALWAYS set this last, even on failure
```

Never let an exception in a background thread propagate — it would silently kill the thread with no recovery.

## Rate Limits & Refresh Timing

- AI analysis: triggered by render loop when `not ai_state['updating']` and market data fresh
- BTC price: background thread, refresh every ~10s
- Market prices: background thread, refresh every `interval` seconds (default 3)
- CoinGecko has a soft rate limit — 5s timeout protects against hangs

## `.env` Loading

```python
# At module top, before client init:
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('OPENAI_API_KEY='):   # or OPENROUTER_API_KEY=
                os.environ['KEY_NAME'] = line.split('=', 1)[1].strip()
except FileNotFoundError:
    pass
```

Must be called before `client = OpenAI()`. The split `'=', 1` handles values containing `=` (base64 keys).
