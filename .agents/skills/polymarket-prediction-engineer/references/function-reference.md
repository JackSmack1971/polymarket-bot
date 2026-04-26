# Function Reference

## poly_ui.py / poly_or.py — Annotated Function Map

### Data Fetching Layer

**`http_get_json(url, timeout=10)`**
- Generic HTTP GET → JSON. Handles raw numeric responses from CLOB.
- Returns: dict | float | None

**`fetch_event_markets(event_id)`**
- Calls `GAMMA_BASE/events/{event_id}`
- Parses `clobTokenIds`, `outcomePrices`, `outcomes`
- Returns: list of `{bracket, yes_token, no_token}`

---

### Display Layer

**`draw_price_chart(stdscr, start_row, start_col, width, height, ai_prices, btc_prices)`**
- Draws Bloomberg-style price comparison chart.
- Parameters: `ai_prices` and `btc_prices` (lists of floats).

**`wrap_ai_text(text, width, model="AI", effort="")`**
- Wraps AI insight string to terminal column width.
- Prepends model name prefix (e.g. `[gpt-5-mini-high]>`).

---

### AI Layer ★ (Most Important)

**`update_ai_analysis_async(current_data, previous_data, ai_state, lock)`**
- Called from background thread every 30s.
- `current_data`: Latest market snapshot.
- `previous_data`: Market snapshot from last cycle.
- `ai_state`: Shared state dict for results and history.
- `lock`: `threading.Lock()` for thread safety.

**`extract_ai_price(ai_text)`**
- Regex: `r'\$([0-9,]+)'` → first match.
- Converts matched string to float (strips commas).

---

### Application Entry

**`main(stdscr, event_id, interval, hist)`**
- Initializes curses and background threads.
- Spawns daemon threads for:
    - `collect_market_data_async` (25s)
    - `update_ai_analysis_async` (30s)
    - `update_btc_price_async` (60s)

---

## State Architecture (Decoupled)

The application uses three separate state dictionaries protected by a single `state_lock`:

```python
ai_state = {
    'analysis': str,             # Raw AI response
    'last_update': float,        # timestamp
    'previous_data': dict,       # for trend analysis
    'updating': bool,            # threading guard
    'conversation_history': [],  # sliced to [-16:]
    'model': str,                # e.g., "gpt-5-mini"
    'effort': str                # e.g., "high"
}

market_state = {
    'current_data': dict,        # JSON formatted for AI
    'last_update': float,
    'updating': bool
}

btc_state = {
    'price': float,              # Live BTC price
    'last_update': float,
    'updating': bool
}
```

---

## Common Bug Locations

| Bug | File | Location | Fix |
|-----|------|----------|-----|
| Race condition on state | both | `main()` loop | Use `with state_lock:` for all reads/writes |
| `updating` stuck at True | both | `update_..._async()` | Ensure `updating = False` in `finally` block |
| History grows unbounded | both | `update_ai_analysis_async()` | Ensure `[-16:]` slice applied |
| OpenRouter reasoning error | `poly_or.py` | `update_ai_analysis_async()` | Remove `reasoning=` kwarg |
