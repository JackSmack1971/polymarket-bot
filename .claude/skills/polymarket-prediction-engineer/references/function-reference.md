# Function Reference

## poly_ui.py / poly_or.py — Annotated Function Map

Both files share identical structure. Differences noted inline.

---

### Data Fetching Layer

**`http_get_json(url, timeout=10)`**
- Generic HTTP GET → JSON. Handles raw numeric responses from CLOB.
- Returns: dict | float | None
- Do not modify timeout below 5s — Gamma API can be slow.

**`fetch_event_markets(event_id)`**
- Calls `GAMMA_BASE/events/{event_id}`
- Parses `clobTokenIds`, `outcomePrices`, `outcomes`
- Filters: only Yes/No markets with 2 tokens
- Sorts brackets: `<$Xk` → `between` → `>$Xk`
- Returns: list of `{bracket, yes_token, no_token}`

**`fetch_price(token_id, side="buy")`**
- Calls `CLOB_BASE/price?token_id={id}&side={side}`
- Returns: float | None
- Side: "buy" = probability of YES outcome

---

### Display Layer

**`spark_segments(values, width=12)`**
- Converts probability history list → sparkline chars (`▁▂▃▄▅▆▇█`)
- Returns list of `(char, delta)` where delta ∈ {-1, 0, +1}

**`wrap_ai_text(text, width, prefix)`**
- Wraps AI insight string to terminal column width
- Prepends model name prefix (e.g. `[gpt-5-mini]>`)
- **Safety net opportunity**: add hard truncation here if format drift occurs

**`draw_screen(stdscr, state)`**
- Main curses render function
- Reads `state` dict: `{markets, ai_text, btc_price, chart_data}`
- Terminal width >95 required for price chart panel

---

### AI Layer ★ (Most Important)

**`update_ai_analysis_async(state, loop)`** — *poly_ui.py*
- Called from background thread every refresh cycle
- Builds `messages` list with system prompt + history
- Calls `client.responses.create(model="gpt-5-mini", reasoning=...)`
- Extracts `.output_text`
- Appends exchange to `state["conversation_history"]`
- Truncates history to last 16 messages

**`update_ai_analysis_async(state, loop)`** — *poly_or.py*
- Same structure, different call:
  `client.chat.completions.create(model="moonshotai/kimi-k2", messages=...)`
- No reasoning parameter
- Extracts `.choices[0].message.content`

**`extract_ai_price(text)`**
- Regex: `r'\$([0-9,]+)'` → first match
- Converts matched string to float (strips commas)
- Returns: float | None
- **Fragile**: depends on exact `$XXX,XXX` format in response

---

### Application Entry

**`main(event_id, interval, history_len)`**
- Initializes curses, state dict, background threads
- Spawns: market fetch thread, AI analysis thread, BTC price thread
- Refresh: every `interval` seconds (default 3)

---

## State Dict Schema

```python
state = {
    "markets": [                    # list of bracket dicts
        {
            "bracket": str,         # question text
            "yes_price": float,
            "no_price": float,
            "yes_history": [float], # sparkline data
            "direction": str,       # "▲" | "▼" | "▬"
        }
    ],
    "ai_text": str,                 # last AI output line
    "ai_price": float | None,       # parsed from ai_text
    "btc_price": float | None,      # live CoinGecko price
    "chart_data": {
        "ai_prices": [float],       # AI prediction history
        "btc_prices": [float],      # real BTC price history
    },
    "conversation_history": [       # OpenAI message objects
        {"role": "user"|"assistant", "content": str}
    ],
}
```

---

## Common Bug Locations

| Bug | File | Location | Fix |
|-----|------|----------|-----|
| Price regex fails | both | `extract_ai_price()` | Add few-shot to system prompt |
| History grows unbounded | both | `update_ai_analysis_async()` | Ensure `[-16:]` slice applied |
| Chart panel missing | both | `draw_screen()` | Check terminal width > 95 |
| API error on reasoning param | `poly_or.py` | `update_ai_analysis_async()` | Remove `reasoning=` kwarg |
| `.env` key not loading | both | top-level file open | Add `OPENROUTER_API_KEY` branch |
