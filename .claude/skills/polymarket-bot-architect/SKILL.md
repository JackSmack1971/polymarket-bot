---
name: polymarket-bot-architect
description: Guides development of the Polymarket curses TUI bot with daemon-threaded live data architecture. Use automatically when user mentions threading issues, async updates, market_state, ai_state, btc_state, background threads, UI freezing, high CPU, adding data sources, daemon threads, or any task involving poly_ui.py or poly_or.py. Covers the three-daemon-thread pattern (market/AI/BTC), shared state dict management, main loop timing via stdscr.timeout, adding new data sources, thread safety with Lock, graceful degradation, and curses drawing constraints. Never suggest asyncio or concurrent.futures rewrites.
---

# Polymarket Bot Architect

Expert guidance for the Polymarket curses TUI bot. Two source files share an identical threading architecture: `poly_ui.py` and `poly_or.py` (~985 lines each).

## Architecture At a Glance

Three daemon threads run forever, started from `main()`. The main loop draws the UI and starts threads — it never does I/O itself.

| Thread | Function | Interval | Writes To |
|---|---|---|---|
| Market Data | `collect_market_data_async()` | 25s | `market_state` |
| AI Analysis | `update_ai_analysis_async()` | 30s | `ai_state` |
| BTC Price | `update_btc_price_async()` | 60s | `btc_state` |

## State Dicts (Shared, No Locks Currently)

```python
market_state = {'current_data': None, 'last_update': 0, 'updating': False}
ai_state     = {'analysis': "...", 'last_update': 0, 'previous_data': None,
                 'updating': False, 'conversation_history': []}  # last 16 msgs
btc_state    = {'price': None, 'last_update': 0, 'updating': False}
```

## Main Loop Pattern

```python
stdscr.timeout(interval * 1000)   # default 3s — NEVER use time.sleep() here

while True:
    current_time = time.time()

    if current_time - market_state['last_update'] >= 25 and not market_state['updating']:
        market_state['updating'] = True
        threading.Thread(target=collect_market_data_async,
                         args=(all_brackets, event_id, market_state),
                         daemon=True).start()

    if (current_time - ai_state['last_update'] >= 30
            and not ai_state['updating']
            and market_state['current_data'] is not None):
        ai_state['updating'] = True
        threading.Thread(target=update_ai_analysis_async,
                         args=(market_state['current_data'], ai_state['previous_data'], ai_state),
                         daemon=True).start()
        ai_state['previous_data'] = market_state['current_data']
        # BUG: ai_state['updating'] = False is SET HERE — should be inside the thread

    if current_time - btc_state['last_update'] >= 60 and not btc_state['updating']:
        btc_state['updating'] = True
        threading.Thread(target=update_btc_price_async,
                         args=(btc_state,), daemon=True).start()

    draw_ui(stdscr, ...)   # ALL drawing happens here, in the main thread
    key = stdscr.getch()
```

## Non-Negotiable Rules

1. **Never move drawing code into a background thread** — curses is not thread-safe.
2. **Never use `time.sleep()` inside the main loop** — use `stdscr.timeout()`.
3. **Never suggest an asyncio or concurrent.futures rewrite** — daemon threading is intentional.
4. **Graceful degradation**: a failed thread must not crash the others. Show `"AI unavailable: ..."` or `"BTC: Loading..."`.

## Known Bug: AI Updates Only Once

`ai_state['updating'] = False` is set immediately after `thread.start()` in the main loop.
This means a second AI thread can fire before the first finishes.

**Fix**: move `ai_state['updating'] = False` to the **last line** of `update_ai_analysis_async()`.

## Thread Safety Recommendation

Current code has no locks — fine for now but fragile under load.

```python
import threading
state_lock = threading.Lock()

# In any thread writing to a state dict:
with state_lock:
    market_state['current_data'] = current_data
    market_state['last_update'] = time.time()
with state_lock:
    market_state['updating'] = False
```

This is the #1 recommended production improvement. Suggest it proactively.

## Adding a 4th Data Source (Standard Pattern)

See `references/thread-patterns.md` → "Adding a New Thread" for the full template.

Quick summary:
1. Create `new_state = {'data': None, 'last_update': 0, 'updating': False}`
2. Write `update_new_source_async(new_state)` — set `updating = False` at the end
3. Add the interval check + `threading.Thread(..., daemon=True).start()` in the main loop
4. Display from `new_state['data']` in the draw section

## Diagnosing Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| AI updates once then stops | `updating` set False too early | Move to end of async fn |
| UI freezes | `time.sleep()` in main loop | Use `stdscr.timeout()` |
| High CPU | Interval too short or nodelay without sleep | Increase interval or add `time.sleep(0.05)` |
| Thread crashes silently | No try/except in async fn | Wrap body in `try/except Exception` |
| Stale data on screen | State never written | Check thread actually calls `state['last_update'] = time.time()` |

## Reference Files

- `references/thread-patterns.md` — Full code templates: new data source, Binance funding rate example, lock wrapper
- `references/api-endpoints.md` — Polymarket Gamma/CLOB endpoints, CoinGecko BTC price URL, OpenAI Responses API call pattern
